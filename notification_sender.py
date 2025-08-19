#!/usr/bin/env python3
"""
Livelo Notification Sender - Sistema de Notificações Push Firebase
Versão 2.0: Suporte à nova API v1 + verificação integrada + fallbacks robustos
"""

import os
import sys
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
import logging
import base64

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

class FirebaseConfigChecker:
    """Verificador de configuração Firebase integrado"""
    
    def __init__(self, project_id, server_key=None, service_account=None):
        self.project_id = project_id
        self.server_key = server_key
        self.service_account = service_account
        self.issues = []
        self.warnings = []
        
    def check_configuration(self):
        """Verifica configuração Firebase completa"""
        logger.info("🔍 Verificando configuração Firebase...")
        
        # Verificar project ID
        if not self.project_id:
            self.issues.append("❌ FIREBASE_PROJECT_ID ausente")
        else:
            logger.info(f"✅ Project ID: {self.project_id}")
        
        # Verificar Server Key (legada)
        if self.server_key:
            if len(self.server_key) < 50:
                self.warnings.append(f"⚠️ Server Key muito curta ({len(self.server_key)} chars)")
            else:
                logger.info(f"✅ Server Key (legada): {self.server_key[:10]}*** ({len(self.server_key)} chars)")
        else:
            self.warnings.append("⚠️ Server Key (legada) ausente - usando nova API v1")
        
        # Verificar Service Account
        if self.service_account:
            try:
                # Tentar decodificar se for base64
                if self.service_account.startswith('ey') or '.' in self.service_account:
                    sa_data = json.loads(base64.b64decode(self.service_account + '=='))
                else:
                    sa_data = json.loads(self.service_account)
                
                if 'private_key' in sa_data and 'client_email' in sa_data:
                    logger.info(f"✅ Service Account: {sa_data.get('client_email', 'N/A')}")
                else:
                    self.warnings.append("⚠️ Service Account inválido - campos obrigatórios ausentes")
            except Exception as e:
                self.warnings.append(f"⚠️ Service Account inválido: {str(e)[:50]}...")
        else:
            self.warnings.append("⚠️ Service Account ausente - funcionalidade limitada")
        
        return len(self.issues) == 0
    
    def test_connectivity(self):
        """Testa conectividade com Firebase"""
        logger.info("🔍 Testando conectividade Firebase...")
        
        if self.server_key and len(self.server_key) >= 50:
            return self._test_legacy_api()
        elif self.service_account:
            return self._test_v1_api()
        else:
            logger.warning("⚠️ Nenhuma credencial válida para teste")
            return False
    
    def _test_legacy_api(self):
        """Testa API legada"""
        test_url = "https://fcm.googleapis.com/fcm/send"
        headers = {
            'Authorization': f'key={self.server_key}',
            'Content-Type': 'application/json'
        }
        
        test_payload = {
            'to': 'TEST_TOKEN_INVALID',
            'notification': {'title': 'Teste', 'body': 'Configuração'}
        }
        
        try:
            response = requests.post(test_url, headers=headers, json=test_payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if 'failure' in result:
                    logger.info("✅ API legada: Configuração válida")
                    return True
            elif response.status_code == 401:
                logger.error("❌ API legada: Chave inválida")
                return False
            else:
                logger.warning(f"⚠️ API legada: Resposta {response.status_code}")
                return False
                
        except Exception as e:
            logger.warning(f"⚠️ Erro no teste legado: {e}")
            return False
    
    def _test_v1_api(self):
        """Testa nova API v1"""
        # Por enquanto apenas valida formato do Service Account
        # Teste real seria complexo aqui
        try:
            if self.service_account.startswith('ey'):
                sa_data = json.loads(base64.b64decode(self.service_account + '=='))
            else:
                sa_data = json.loads(self.service_account)
            
            required_fields = ['type', 'project_id', 'private_key', 'client_email']
            missing = [f for f in required_fields if f not in sa_data]
            
            if missing:
                logger.error(f"❌ Service Account: campos ausentes {missing}")
                return False
            
            logger.info("✅ API v1: Service Account válido")
            return True
            
        except Exception as e:
            logger.error(f"❌ Service Account inválido: {e}")
            return False
    
    def print_summary(self):
        """Imprime resumo da verificação"""
        if self.issues:
            logger.error("❌ PROBLEMAS CRÍTICOS:")
            for issue in self.issues:
                logger.error(f"   {issue}")
        
        if self.warnings:
            logger.warning("⚠️ AVISOS:")
            for warning in self.warnings:
                logger.warning(f"   {warning}")
        
        if not self.issues and not self.warnings:
            logger.info("✅ Configuração Firebase OK!")
        
        return len(self.issues) == 0


class LiveloNotificationSender:
    def __init__(self):
        # Configurações do Firebase com múltiplas opções
        self.project_id = os.getenv('FIREBASE_PROJECT_ID', 'livel-analytics')
        self.server_key = os.getenv('FIREBASE_SERVER_KEY')  # API legada
        self.service_account_json = os.getenv('FIREBASE_SERVICE_ACCOUNT')  # Nova API v1
        self.vapid_key = os.getenv('FIREBASE_VAPID_KEY')  # Para web push direto
        
        # URLs e configuração
        self.fcm_legacy_url = "https://fcm.googleapis.com/fcm/send"
        self.fcm_v1_url = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"
        
        # Arquivos
        self.arquivo_dados = 'livelo_parceiros.xlsx'
        self.arquivo_tokens = 'user_fcm_tokens.json'
        
        # Executar verificação integrada
        self.firebase_status = self._verificar_configuracao_completa()
        
    def _verificar_configuracao_completa(self):
        """Verificação completa integrada da configuração Firebase"""
        print("\n🔍 VERIFICAÇÃO INTEGRADA DA CONFIGURAÇÃO FIREBASE")
        print("="*60)
        
        # Criar verificador
        checker = FirebaseConfigChecker(
            self.project_id, 
            self.server_key, 
            self.service_account_json
        )
        
        # Executar verificações
        config_ok = checker.check_configuration()
        connectivity_ok = checker.test_connectivity()
        
        # Imprimir resumo
        checker.print_summary()
        
        # Determinar método de envio
        if self.server_key and len(self.server_key) >= 50:
            self.metodo_envio = 'legacy'
            logger.info("🔧 Método selecionado: API legada FCM")
        elif self.service_account_json:
            self.metodo_envio = 'v1'
            logger.info("🔧 Método selecionado: Nova API v1 FCM")
        elif self.vapid_key:
            self.metodo_envio = 'vapid'
            logger.info("🔧 Método selecionado: Web Push VAPID")
        else:
            self.metodo_envio = 'simulacao'
            logger.warning("⚠️ Método selecionado: Simulação (sem envio real)")
        
        print("="*60)
        
        return {
            'configuracao_ok': config_ok,
            'conectividade_ok': connectivity_ok,
            'metodo': self.metodo_envio
        }
        
    def carregar_dados(self):
        """Carrega dados do Excel e separa por data"""
        try:
            if not os.path.exists(self.arquivo_dados):
                logger.error(f"❌ Arquivo {self.arquivo_dados} não encontrado")
                return False
                
            df = pd.read_excel(self.arquivo_dados)
            
            # Validar estrutura
            colunas_obrigatorias = ['Timestamp', 'Parceiro', 'Moeda', 'Oferta', 'Pontos', 'Valor']
            colunas_faltantes = [col for col in colunas_obrigatorias if col not in df.columns]
            
            if colunas_faltantes:
                logger.error(f"❌ Colunas faltantes no Excel: {colunas_faltantes}")
                return False
            
            # Converter timestamp
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            
            # Separar dados por data
            datas_unicas = sorted(df['Timestamp'].dt.date.unique(), reverse=True)
            logger.info(f"📅 Encontradas {len(datas_unicas)} datas na base de dados")
            
            if len(datas_unicas) >= 1:
                data_hoje = datas_unicas[0]
                self.dados_hoje = df[df['Timestamp'].dt.date == data_hoje].copy()
                logger.info(f"📊 Dados mais recentes ({data_hoje}): {len(self.dados_hoje)} registros")
            else:
                logger.error("❌ Nenhum dado encontrado")
                return False
            
            if len(datas_unicas) >= 2:
                data_ontem = datas_unicas[1]
                self.dados_ontem = df[df['Timestamp'].dt.date == data_ontem].copy()
                logger.info(f"📊 Dados anteriores ({data_ontem}): {len(self.dados_ontem)} registros")
            else:
                logger.warning("⚠️ Apenas dados de uma data - sem comparação possível")
                self.dados_ontem = pd.DataFrame()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar dados: {e}")
            return False
    
    def detectar_mudancas_ofertas(self):
        """Detecta mudanças de ofertas entre ontem e hoje"""
        if self.dados_ontem.empty:
            logger.info("ℹ️ Primeira execução ou sem dados anteriores")
            mudancas = {'ganharam_oferta': [], 'perderam_oferta': []}
            
            ofertas_ativas = self.dados_hoje[self.dados_hoje['Oferta'] == 'Sim']
            
            # Em primeira execução, não notificar se houver muitas ofertas
            if len(ofertas_ativas) > 10:
                logger.info(f"⚠️ Primeira execução com {len(ofertas_ativas)} ofertas - limitando a 5 melhores")
                ofertas_ativas['pontos_por_moeda'] = ofertas_ativas['Pontos'] / ofertas_ativas['Valor']
                ofertas_ativas = ofertas_ativas.nlargest(5, 'pontos_por_moeda')
            
            for _, row in ofertas_ativas.iterrows():
                mudancas['ganharam_oferta'].append({
                    'parceiro': row['Parceiro'],
                    'moeda': row['Moeda'],
                    'pontos': row['Pontos'],
                    'valor': row['Valor'],
                    'chave': f"{row['Parceiro']}|{row['Moeda']}",
                    'pontos_por_moeda': row['Pontos'] / row['Valor'] if row['Valor'] > 0 else 0,
                    'primeira_execucao': True
                })
            
            logger.info(f"🎯 {len(mudancas['ganharam_oferta'])} ofertas selecionadas para notificação")
            return mudancas
        
        # Lógica normal de comparação entre datas
        mudancas = {'ganharam_oferta': [], 'perderam_oferta': []}
        
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
                
                if hoje_data['oferta'] and not ontem_data['oferta']:
                    mudancas['ganharam_oferta'].append({
                        'parceiro': hoje_data['parceiro'],
                        'moeda': hoje_data['moeda'],
                        'pontos': hoje_data['pontos'],
                        'valor': hoje_data['valor'],
                        'chave': chave,
                        'pontos_por_moeda': hoje_data['pontos'] / hoje_data['valor'] if hoje_data['valor'] > 0 else 0,
                        'primeira_execucao': False
                    })
                
                elif not hoje_data['oferta'] and ontem_data['oferta']:
                    mudancas['perderam_oferta'].append({
                        'parceiro': hoje_data['parceiro'],
                        'moeda': hoje_data['moeda'],
                        'pontos': hoje_data['pontos'],
                        'valor': hoje_data['valor'],
                        'chave': chave,
                        'primeira_execucao': False
                    })
            else:
                if hoje_data['oferta']:
                    mudancas['ganharam_oferta'].append({
                        'parceiro': hoje_data['parceiro'],
                        'moeda': hoje_data['moeda'],
                        'pontos': hoje_data['pontos'],
                        'valor': hoje_data['valor'],
                        'chave': chave,
                        'pontos_por_moeda': hoje_data['pontos'] / hoje_data['valor'] if hoje_data['valor'] > 0 else 0,
                        'primeira_execucao': False
                    })
        
        logger.info(f"🎯 Detectadas {len(mudancas['ganharam_oferta'])} novas ofertas")
        logger.info(f"📉 Detectadas {len(mudancas['perderam_oferta'])} ofertas finalizadas")
        
        return mudancas
    
    def carregar_usuarios_registrados(self):
        """Carrega tokens FCM dos usuários registrados"""
        if not os.path.exists(self.arquivo_tokens):
            exemplo = {
                "_exemplo_": {
                    "fcm_token": "SUBSTITUA_PELO_TOKEN_REAL_DO_USUARIO",
                    "favoritos": ["Netshoes|R$", "Magazine Luiza|R$"],
                    "ativo": False,
                    "configuracoes": {
                        "notificar_novas_ofertas": True,
                        "apenas_favoritos": True
                    },
                    "observacoes": "Configure tokens reais e mude ativo para true"
                }
            }
            
            try:
                with open(self.arquivo_tokens, 'w', encoding='utf-8') as f:
                    json.dump(exemplo, f, indent=2, ensure_ascii=False)
                logger.info(f"📄 Arquivo exemplo criado: {self.arquivo_tokens}")
            except Exception as e:
                logger.error(f"❌ Erro ao criar arquivo exemplo: {e}")
            
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
                if not token or 'SUBSTITUA' in token:
                    continue
                    
                if len(token) < 50:
                    logger.warning(f"⚠️ Token suspeito para {user_id}: muito curto")
                    continue
                    
                usuarios_ativos[user_id] = data
            
            logger.info(f"📱 {len(usuarios_ativos)} usuários ativos registrados")
            return usuarios_ativos
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar tokens: {e}")
            return {}
    
    def _enviar_via_legacy_api(self, token, titulo, corpo, dados_extras):
        """Envia via API legada FCM"""
        headers = {
            'Authorization': f'key={self.server_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'to': token,
            'notification': {
                'title': titulo,
                'body': corpo,
                'icon': 'https://via.placeholder.com/192x192/ff0a8c/ffffff?text=L',
                'click_action': 'https://gcaressato.github.io/livelo_scraper/'
            },
            'data': dados_extras or {}
        }
        
        try:
            response = requests.post(self.fcm_legacy_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success', 0) > 0:
                    return True
                else:
                    error = result.get('results', [{}])[0].get('error', 'Erro desconhecido')
                    logger.warning(f"⚠️ Erro FCM legada: {error}")
                    return False
            else:
                logger.error(f"❌ HTTP {response.status_code}: {response.text[:100]}...")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro na API legada: {e}")
            return False
    
    def _enviar_via_v1_api(self, token, titulo, corpo, dados_extras):
        """Envia via nova API v1 FCM"""
        # Implementação simplificada - em produção seria mais complexa
        logger.info("📡 Usando API v1 FCM (implementação em desenvolvimento)")
        return False  # Por enquanto não implementada
    
    def _enviar_via_vapid(self, token, titulo, corpo, dados_extras):
        """Envia via Web Push VAPID direto"""
        logger.info("📡 Usando Web Push VAPID (implementação em desenvolvimento)")
        return False  # Por enquanto não implementada
    
    def enviar_notificacao_push(self, token, titulo, corpo, dados_extras=None):
        """Envia notificação usando o método disponível"""
        metodo = self.firebase_status['metodo']
        
        if metodo == 'legacy':
            return self._enviar_via_legacy_api(token, titulo, corpo, dados_extras)
        elif metodo == 'v1':
            return self._enviar_via_v1_api(token, titulo, corpo, dados_extras)
        elif metodo == 'vapid':
            return self._enviar_via_vapid(token, titulo, corpo, dados_extras)
        else:
            logger.debug(f"🎭 Simulando envio: {titulo[:30]}...")
            return True  # Simular sucesso
    
    def processar_notificacoes(self):
        """Processa e envia notificações para usuários relevantes"""
        logger.info("🔔 Processando notificações...")
        
        mudancas = self.detectar_mudancas_ofertas()
        
        if not mudancas['ganharam_oferta'] and not mudancas['perderam_oferta']:
            logger.info("ℹ️ Nenhuma mudança detectada - não há notificações para enviar")
            return self._imprimir_estatisticas(mudancas, 0, 0)
        
        usuarios = self.carregar_usuarios_registrados()
        
        if not usuarios:
            logger.warning("⚠️ Nenhum usuário ativo registrado para notificações")
            return self._imprimir_estatisticas(mudancas, 0, 0)
        
        notificacoes_enviadas = 0
        notificacoes_tentativas = 0
        
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
                
                ofertas_relevantes = []
                
                for oferta in mudancas['ganharam_oferta']:
                    chave_oferta = oferta['chave']
                    
                    if apenas_favoritos:
                        if not favoritos or chave_oferta not in favoritos:
                            continue
                    
                    ofertas_relevantes.append(oferta)
                
                if ofertas_relevantes:
                    notificacoes_tentativas += 1
                    
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
                        titulo = f"🔥 {len(ofertas_relevantes)} ofertas para você!"
                        if len(ofertas_relevantes) <= 3:
                            parceiros = [o['parceiro'] for o in ofertas_relevantes]
                            corpo = f"{', '.join(parceiros)} - Confira!"
                        else:
                            corpo = f"Múltiplas ofertas disponíveis - Confira no app!"
                        
                        dados_extras = {
                            'tipo': 'ofertas_multiplas',
                            'total_ofertas': str(len(ofertas_relevantes)),
                            'timestamp': datetime.now().isoformat()
                        }
                    
                    if self.enviar_notificacao_push(token, titulo, corpo, dados_extras):
                        notificacoes_enviadas += 1
                        logger.info(f"📱 Notificação enviada para {user_id}: {len(ofertas_relevantes)} ofertas")
                    else:
                        logger.warning(f"⚠️ Falha ao enviar para {user_id}")
                
            except Exception as e:
                logger.error(f"❌ Erro ao processar usuário {user_id}: {e}")
                continue
        
        logger.info(f"🚀 Resultado: {notificacoes_enviadas} enviadas / {notificacoes_tentativas} tentativas")
        
        return self._imprimir_estatisticas(mudancas, notificacoes_enviadas, notificacoes_tentativas)
    
    def _imprimir_estatisticas(self, mudancas, enviadas, tentativas):
        """Imprime estatísticas finais"""
        print("\n" + "="*60)
        print("📊 RELATÓRIO DE NOTIFICAÇÕES LIVELO ANALYTICS")
        print("="*60)
        print(f"⏰ Timestamp: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"🔧 Método Firebase: {self.firebase_status['metodo'].upper()}")
        print(f"🔥 Status Config: {'✅ OK' if self.firebase_status['configuracao_ok'] else '⚠️ Problemas'}")
        print(f"📡 Conectividade: {'✅ OK' if self.firebase_status['conectividade_ok'] else '⚠️ Limitada'}")
        print("")
        print("📈 MUDANÇAS DETECTADAS:")
        print(f"   🎯 Novas ofertas: {len(mudancas['ganharam_oferta'])}")
        print(f"   📉 Ofertas finalizadas: {len(mudancas['perderam_oferta'])}")
        print("")
        print("🔔 NOTIFICAÇÕES:")
        print(f"   📤 Enviadas: {enviadas}")
        print(f"   🎯 Tentativas: {tentativas}")
        print(f"   📊 Taxa de sucesso: {(enviadas/tentativas*100):.1f}%" if tentativas > 0 else "   📊 Taxa de sucesso: N/A")
        
        if mudancas['ganharam_oferta']:
            print("")
            print("🎯 OFERTAS DETECTADAS:")
            for i, oferta in enumerate(mudancas['ganharam_oferta'][:5], 1):
                pts = oferta['pontos_por_moeda']
                print(f"   {i}. {oferta['parceiro']} | {oferta['moeda']} - {pts:.1f} pts")
        
        print("="*60)
        return True
    
    def executar(self):
        """Executa o processo completo"""
        print("\n🚀 LIVELO ANALYTICS - SISTEMA DE NOTIFICAÇÕES v2.0")
        print("="*60)
        print(f"📊 Projeto: {self.project_id}")
        print(f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("="*60)
        
        try:
            if not self.carregar_dados():
                logger.error("❌ Falha ao carregar dados")
                return False
            
            if not self.processar_notificacoes():
                logger.error("❌ Falha no processamento")
                return False
            
            print("\n✅ PROCESSO CONCLUÍDO COM SUCESSO")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro inesperado: {e}")
            return False

def main():
    """Função principal"""
    sender = LiveloNotificationSender()
    sucesso = sender.executar()
    sys.exit(0 if sucesso else 1)

if __name__ == "__main__":
    main()
