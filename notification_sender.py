#!/usr/bin/env python3
"""
Livelo Notification Sender - Sistema de Notificações Push Firebase
Versão 3.0: API moderna APENAS (sem dependência de chaves legadas)
"""

import os
import sys
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
import logging
import base64
from google.oauth2 import service_account
from google.auth.transport.requests import Request

# Configurar logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('notifications.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FirebaseModernSender:
    """Sistema de notificações usando apenas APIs modernas do Firebase"""
    
    def __init__(self):
        self.project_id = os.getenv('FIREBASE_PROJECT_ID', 'livel-analytics')
        self.api_key = os.getenv('FIREBASE_API_KEY')
        self.app_id = os.getenv('FIREBASE_APP_ID') 
        self.sender_id = os.getenv('FIREBASE_SENDER_ID')
        self.service_account_json = os.getenv('FIREBASE_SERVICE_ACCOUNT')
        self.vapid_key = os.getenv('FIREBASE_VAPID_KEY')
        
        # URLs modernas
        self.fcm_v1_url = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"
        
        # Arquivos
        self.arquivo_dados = 'livelo_parceiros.xlsx'
        self.arquivo_tokens = 'user_fcm_tokens.json'
        
        # Status de inicialização
        self.firebase_ready = self._verificar_configuracao()
        
    def _verificar_configuracao(self):
        """Verifica configuração Firebase moderna"""
        print("\n🔍 VERIFICAÇÃO FIREBASE API MODERNA")
        print("="*60)
        
        configs = {
            'Project ID': self.project_id,
            'API Key': self.api_key,
            'App ID': self.app_id,
            'Sender ID': self.sender_id,
            'Service Account': self.service_account_json,
            'VAPID Key': self.vapid_key
        }
        
        configured_count = 0
        
        for name, value in configs.items():
            if value:
                if 'Key' in name or 'Account' in name:
                    logger.info(f"✅ {name}: {value[:20]}*** ({len(value)} chars)")
                else:
                    logger.info(f"✅ {name}: {value}")
                configured_count += 1
            else:
                logger.warning(f"⚠️ {name}: AUSENTE")
        
        logger.info(f"📊 Configuração: {configured_count}/6 campos configurados")
        
        # Determinar método preferencial
        if self.service_account_json and len(self.service_account_json) > 100:
            self.metodo = 'fcm_v1'
            logger.info("🚀 Método: FCM API v1 (Service Account)")
            return self._setup_service_account()
        elif self.vapid_key and len(self.vapid_key) > 40:
            self.metodo = 'web_push'
            logger.info("🚀 Método: Web Push VAPID")
            return True
        else:
            self.metodo = 'simulacao'
            logger.warning("⚠️ Método: Simulação (configuração insuficiente)")
            return False
    
    def _setup_service_account(self):
        """Configura Service Account para FCM v1"""
        try:
            # Decodificar Service Account JSON
            if self.service_account_json.startswith('{'):
                sa_data = json.loads(self.service_account_json)
            else:
                # Se for base64 encoded
                sa_data = json.loads(base64.b64decode(self.service_account_json))
            
            # Criar credenciais
            self.credentials = service_account.Credentials.from_service_account_info(
                sa_data,
                scopes=['https://www.googleapis.com/auth/firebase.messaging']
            )
            
            logger.info(f"✅ Service Account configurado: {sa_data.get('client_email', 'N/A')}")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Service Account JSON inválido: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Erro configurando Service Account: {e}")
            return False
    
    def _get_access_token(self):
        """Obtém token de acesso para FCM v1"""
        try:
            self.credentials.refresh(Request())
            return self.credentials.token
        except Exception as e:
            logger.error(f"❌ Erro obtendo access token: {e}")
            return None
    
    def carregar_dados(self):
        """Carrega dados do Excel"""
        try:
            if not os.path.exists(self.arquivo_dados):
                logger.error(f"❌ Arquivo {self.arquivo_dados} não encontrado")
                return False
                
            df = pd.read_excel(self.arquivo_dados)
            
            # Validar estrutura
            colunas_obrigatorias = ['Timestamp', 'Parceiro', 'Moeda', 'Oferta', 'Pontos', 'Valor']
            colunas_faltantes = [col for col in colunas_obrigatorias if col not in df.columns]
            
            if colunas_faltantes:
                logger.error(f"❌ Colunas faltantes: {colunas_faltantes}")
                return False
            
            # Converter timestamp
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            
            # Separar por data
            datas_unicas = sorted(df['Timestamp'].dt.date.unique(), reverse=True)
            logger.info(f"📅 Encontradas {len(datas_unicas)} datas")
            
            if len(datas_unicas) >= 1:
                data_hoje = datas_unicas[0]
                self.dados_hoje = df[df['Timestamp'].dt.date == data_hoje].copy()
                logger.info(f"📊 Dados recentes ({data_hoje}): {len(self.dados_hoje)} registros")
            else:
                logger.error("❌ Nenhum dado encontrado")
                return False
            
            if len(datas_unicas) >= 2:
                data_ontem = datas_unicas[1]
                self.dados_ontem = df[df['Timestamp'].dt.date == data_ontem].copy()
                logger.info(f"📊 Dados anteriores ({data_ontem}): {len(self.dados_ontem)} registros")
            else:
                logger.warning("⚠️ Sem dados anteriores para comparação")
                self.dados_ontem = pd.DataFrame()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro carregando dados: {e}")
            return False
    
    def detectar_mudancas(self):
        """Detecta mudanças nas ofertas"""
        if self.dados_ontem.empty:
            logger.info("ℹ️ Primeira execução - selecionando melhores ofertas")
            
            ofertas_ativas = self.dados_hoje[self.dados_hoje['Oferta'] == 'Sim']
            
            # Limitar para evitar spam em primeira execução
            if len(ofertas_ativas) > 10:
                ofertas_ativas['pontos_por_moeda'] = ofertas_ativas['Pontos'] / ofertas_ativas['Valor']
                ofertas_ativas = ofertas_ativas.nlargest(5, 'pontos_por_moeda')
                logger.info(f"⚠️ Limitando a 5 melhores ofertas (de {len(self.dados_hoje)} total)")
            
            mudancas = {'novas': [], 'finalizadas': []}
            
            for _, row in ofertas_ativas.iterrows():
                mudancas['novas'].append({
                    'parceiro': row['Parceiro'],
                    'moeda': row['Moeda'],
                    'pontos': row['Pontos'],
                    'valor': row['Valor'],
                    'chave': f"{row['Parceiro']}|{row['Moeda']}",
                    'pontos_por_moeda': row['Pontos'] / row['Valor'] if row['Valor'] > 0 else 0,
                    'primeira_execucao': True
                })
            
            logger.info(f"🎯 {len(mudancas['novas'])} ofertas selecionadas")
            return mudancas
        
        # Comparação normal entre datas
        mudancas = {'novas': [], 'finalizadas': []}
        
        # Criar dicionários para comparação
        hoje_dict = {}
        for _, row in self.dados_hoje.iterrows():
            chave = f"{row['Parceiro']}|{row['Moeda']}"
            hoje_dict[chave] = {
                'parceiro': row['Parceiro'],
                'moeda': row['Moeda'],
                'oferta': row['Oferta'] == 'Sim',
                'pontos': row['Pontos'],
                'valor': row['Valor']
            }
        
        ontem_dict = {}
        for _, row in self.dados_ontem.iterrows():
            chave = f"{row['Parceiro']}|{row['Moeda']}"
            ontem_dict[chave] = {
                'parceiro': row['Parceiro'],
                'moeda': row['Moeda'],
                'oferta': row['Oferta'] == 'Sim',
                'pontos': row['Pontos'],
                'valor': row['Valor']
            }
        
        # Detectar mudanças
        for chave in hoje_dict:
            hoje_data = hoje_dict[chave]
            
            if chave in ontem_dict:
                ontem_data = ontem_dict[chave]
                
                # Nova oferta
                if hoje_data['oferta'] and not ontem_data['oferta']:
                    mudancas['novas'].append({
                        'parceiro': hoje_data['parceiro'],
                        'moeda': hoje_data['moeda'],
                        'pontos': hoje_data['pontos'],
                        'valor': hoje_data['valor'],
                        'chave': chave,
                        'pontos_por_moeda': hoje_data['pontos'] / hoje_data['valor'] if hoje_data['valor'] > 0 else 0,
                        'primeira_execucao': False
                    })
                
                # Oferta finalizada
                elif not hoje_data['oferta'] and ontem_data['oferta']:
                    mudancas['finalizadas'].append({
                        'parceiro': hoje_data['parceiro'],
                        'moeda': hoje_data['moeda'],
                        'chave': chave
                    })
            else:
                # Novo parceiro com oferta
                if hoje_data['oferta']:
                    mudancas['novas'].append({
                        'parceiro': hoje_data['parceiro'],
                        'moeda': hoje_data['moeda'],
                        'pontos': hoje_data['pontos'],
                        'valor': hoje_data['valor'],
                        'chave': chave,
                        'pontos_por_moeda': hoje_data['pontos'] / hoje_data['valor'] if hoje_data['valor'] > 0 else 0,
                        'primeira_execucao': False
                    })
        
        logger.info(f"🎯 {len(mudancas['novas'])} novas ofertas")
        logger.info(f"📉 {len(mudancas['finalizadas'])} ofertas finalizadas")
        
        return mudancas
    
    def carregar_usuarios(self):
        """Carrega tokens dos usuários registrados"""
        if not os.path.exists(self.arquivo_tokens):
            exemplo = {
                "_exemplo_": {
                    "fcm_token": "COLE_AQUI_O_TOKEN_REAL_DO_USUARIO",
                    "favoritos": ["Netshoes|R$", "Magazine Luiza|R$"],
                    "ativo": False,
                    "configuracoes": {
                        "notificar_novas_ofertas": True,
                        "apenas_favoritos": True
                    },
                    "observacoes": "Mude ativo para true e configure token real"
                }
            }
            
            try:
                with open(self.arquivo_tokens, 'w', encoding='utf-8') as f:
                    json.dump(exemplo, f, indent=2, ensure_ascii=False)
                logger.info(f"📄 Arquivo exemplo criado: {self.arquivo_tokens}")
                logger.info("💡 Para receber notificações:")
                logger.info("   1. Edite o arquivo com tokens reais")
                logger.info("   2. Mude 'ativo' para true")
            except Exception as e:
                logger.error(f"❌ Erro criando arquivo: {e}")
            
            return {}
        
        try:
            with open(self.arquivo_tokens, 'r', encoding='utf-8') as f:
                usuarios = json.load(f)
            
            usuarios_ativos = {}
            for user_id, data in usuarios.items():
                if user_id.startswith('_'):
                    continue
                    
                if not data.get('ativo', False):
                    continue
                    
                token = data.get('fcm_token', '')
                if not token or 'COLE_AQUI' in token:
                    continue
                    
                if len(token) < 50:
                    logger.warning(f"⚠️ Token suspeito para {user_id}")
                    continue
                    
                usuarios_ativos[user_id] = data
            
            logger.info(f"📱 {len(usuarios_ativos)} usuários ativos")
            return usuarios_ativos
            
        except Exception as e:
            logger.error(f"❌ Erro carregando usuários: {e}")
            return {}
    
    def _enviar_fcm_v1(self, token, titulo, corpo, dados_extras):
        """Envia via FCM API v1 (moderna)"""
        if not self.firebase_ready or self.metodo != 'fcm_v1':
            return False
        
        access_token = self._get_access_token()
        if not access_token:
            return False
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'message': {
                'token': token,
                'notification': {
                    'title': titulo,
                    'body': corpo
                },
                'data': dados_extras or {},
                'webpush': {
                    'headers': {
                        'Urgency': 'high'
                    },
                    'notification': {
                        'icon': 'https://via.placeholder.com/192x192/ff0a8c/ffffff?text=L',
                        'badge': 'https://via.placeholder.com/96x96/ff0a8c/ffffff?text=L',
                        'requireInteraction': True,
                        'actions': [
                            {
                                'action': 'view',
                                'title': '👀 Ver Ofertas'
                            }
                        ]
                    }
                }
            }
        }
        
        try:
            response = requests.post(self.fcm_v1_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                logger.info(f"✅ FCM v1 enviado: {titulo[:40]}...")
                return True
            else:
                logger.error(f"❌ FCM v1 erro {response.status_code}: {response.text[:100]}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro FCM v1: {e}")
            return False
    
    def _enviar_web_push(self, token, titulo, corpo, dados_extras):
        """Envia via Web Push VAPID direto"""
        # Por ora, simular - implementação completa de Web Push é complexa
        logger.info(f"📡 Web Push VAPID: {titulo[:40]}... (implementação futura)")
        return True
    
    def _simular_envio(self, token, titulo, corpo, dados_extras):
        """Simula envio para teste"""
        logger.info(f"🎭 Simulando: {titulo[:40]}... para {token[:20]}...")
        return True
    
    def enviar_notificacao(self, token, titulo, corpo, dados_extras=None):
        """Envia notificação usando método disponível"""
        if self.metodo == 'fcm_v1':
            return self._enviar_fcm_v1(token, titulo, corpo, dados_extras)
        elif self.metodo == 'web_push':
            return self._enviar_web_push(token, titulo, corpo, dados_extras)
        else:
            return self._simular_envio(token, titulo, corpo, dados_extras)
    
    def processar_notificacoes(self):
        """Processa e envia notificações"""
        logger.info("🔔 Processando notificações...")
        
        mudancas = self.detectar_mudancas()
        
        if not mudancas['novas'] and not mudancas['finalizadas']:
            logger.info("ℹ️ Nenhuma mudança - não há notificações para enviar")
            return self._imprimir_estatisticas(mudancas, 0, 0)
        
        usuarios = self.carregar_usuarios()
        
        if not usuarios:
            logger.warning("⚠️ Nenhum usuário ativo para notificações")
            return self._imprimir_estatisticas(mudancas, 0, 0)
        
        enviadas = 0
        tentativas = 0
        
        for user_id, user_data in usuarios.items():
            try:
                token = user_data.get('fcm_token', '')
                favoritos = user_data.get('favoritos', [])
                config = user_data.get('configuracoes', {})
                
                if not token:
                    continue
                
                notificar_novas = config.get('notificar_novas_ofertas', True)
                apenas_favoritos = config.get('apenas_favoritos', True)
                
                if not notificar_novas:
                    continue
                
                # Filtrar ofertas relevantes
                ofertas_relevantes = []
                for oferta in mudancas['novas']:
                    if apenas_favoritos:
                        if not favoritos or oferta['chave'] not in favoritos:
                            continue
                    ofertas_relevantes.append(oferta)
                
                if ofertas_relevantes:
                    tentativas += 1
                    
                    # Criar notificação
                    if len(ofertas_relevantes) == 1:
                        oferta = ofertas_relevantes[0]
                        titulo = f"🎯 {oferta['parceiro']} em oferta!"
                        corpo = f"{oferta['pontos_por_moeda']:.1f} pontos por {oferta['moeda']}"
                        dados_extras = {
                            'tipo': 'oferta_individual',
                            'parceiro': oferta['parceiro'],
                            'timestamp': datetime.now().isoformat()
                        }
                    else:
                        titulo = f"🔥 {len(ofertas_relevantes)} ofertas!"
                        if len(ofertas_relevantes) <= 3:
                            parceiros = [o['parceiro'] for o in ofertas_relevantes]
                            corpo = f"{', '.join(parceiros)} - Confira!"
                        else:
                            corpo = f"Múltiplas ofertas nos seus favoritos!"
                        dados_extras = {
                            'tipo': 'ofertas_multiplas',
                            'total': str(len(ofertas_relevantes)),
                            'timestamp': datetime.now().isoformat()
                        }
                    
                    # Enviar
                    if self.enviar_notificacao(token, titulo, corpo, dados_extras):
                        enviadas += 1
                        logger.info(f"📱 Enviado para {user_id}: {len(ofertas_relevantes)} ofertas")
                    else:
                        logger.warning(f"⚠️ Falha para {user_id}")
                
            except Exception as e:
                logger.error(f"❌ Erro processando {user_id}: {e}")
                continue
        
        logger.info(f"🚀 Resultado: {enviadas} enviadas / {tentativas} tentativas")
        return self._imprimir_estatisticas(mudancas, enviadas, tentativas)
    
    def _imprimir_estatisticas(self, mudancas, enviadas, tentativas):
        """Imprime relatório final"""
        print("\n" + "="*60)
        print("📊 RELATÓRIO NOTIFICAÇÕES LIVELO ANALYTICS v3.0")
        print("="*60)
        print(f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"🔧 Método: {self.metodo.upper()}")
        print(f"🔥 Firebase: {'✅ ATIVO' if self.firebase_ready else '❌ INATIVO'}")
        print(f"📡 Status: {'✅ PRONTO' if self.metodo != 'simulacao' else '🎭 SIMULAÇÃO'}")
        print("")
        print("📈 MUDANÇAS:")
        print(f"   🎯 Novas ofertas: {len(mudancas['novas'])}")
        print(f"   📉 Finalizadas: {len(mudancas['finalizadas'])}")
        print("")
        print("🔔 NOTIFICAÇÕES:")
        print(f"   📤 Enviadas: {enviadas}")
        print(f"   🎯 Tentativas: {tentativas}")
        print(f"   📊 Taxa: {(enviadas/tentativas*100):.1f}%" if tentativas > 0 else "   📊 Taxa: N/A")
        
        if mudancas['novas']:
            print("")
            print("🎯 OFERTAS DETECTADAS:")
            for i, oferta in enumerate(mudancas['novas'][:5], 1):
                pts = oferta['pontos_por_moeda']
                print(f"   {i}. {oferta['parceiro']} | {oferta['moeda']} - {pts:.1f} pts")
        
        print("="*60)
        return True
    
    def executar(self):
        """Executa processo completo"""
        print("\n🚀 LIVELO ANALYTICS - NOTIFICAÇÕES v3.0 (API MODERNA)")
        print("="*60)
        print(f"📊 Projeto: {self.project_id}")
        print(f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("="*60)
        
        try:
            if not self.carregar_dados():
                logger.error("❌ Falha carregando dados")
                return False
            
            if not self.processar_notificacoes():
                logger.error("❌ Falha processando notificações")
                return False
            
            print("\n✅ PROCESSO CONCLUÍDO!")
            return True
            
        except KeyboardInterrupt:
            logger.info("⚠️ Processo interrompido")
            return False
        except Exception as e:
            logger.error(f"❌ Erro inesperado: {e}")
            return False


def main():
    """Função principal"""
    try:
        # Instalar dependência se necessária
        try:
            from google.oauth2 import service_account
        except ImportError:
            logger.warning("⚠️ Instalando google-auth...")
            import subprocess
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'google-auth'])
            from google.oauth2 import service_account
        
        sender = FirebaseModernSender()
        sucesso = sender.executar()
        sys.exit(0 if sucesso else 1)
        
    except Exception as e:
        logger.error(f"❌ Erro crítico: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
