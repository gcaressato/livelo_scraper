#!/usr/bin/env python3
"""
Livelo Notification Sender - Sistema de Notificações Push Firebase
Versão limpa e independente para envio de notificações baseadas em mudanças de ofertas
"""

import os
import sys
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
import logging

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

class LiveloNotificationSender:
    def __init__(self):
        # Configurações do Firebase (via environment variables)
        self.project_id = os.getenv('FIREBASE_PROJECT_ID')
        self.server_key = os.getenv('FIREBASE_SERVER_KEY')
        self.fcm_url = "https://fcm.googleapis.com/fcm/send"
        
        # Verificar configuração
        if not self.project_id or not self.server_key:
            logger.error("❌ FIREBASE_PROJECT_ID ou FIREBASE_SERVER_KEY não configurados")
            logger.info("💡 Configure as variáveis de ambiente:")
            logger.info("   export FIREBASE_PROJECT_ID='seu-projeto-id'")
            logger.info("   export FIREBASE_SERVER_KEY='sua-chave-servidor'")
            sys.exit(1)
            
        logger.info(f"✅ Firebase configurado para projeto: ***{self.project_id[-4:]}")
        
        # Dados
        self.dados_hoje = None
        self.dados_ontem = None
        self.arquivo_tokens = 'user_fcm_tokens.json'
        self.arquivo_stats = 'notification_stats.json'
        
    def carregar_dados(self):
        """Carrega dados do Excel e separa por data"""
        try:
            arquivo_dados = 'livelo_parceiros.xlsx'
            if not os.path.exists(arquivo_dados):
                logger.error(f"❌ Arquivo {arquivo_dados} não encontrado")
                return False
                
            df = pd.read_excel(arquivo_dados)
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            
            # Separar dados por data
            datas_unicas = sorted(df['Timestamp'].dt.date.unique(), reverse=True)
            logger.info(f"📅 Encontradas {len(datas_unicas)} datas na base de dados")
            
            if len(datas_unicas) >= 1:
                data_hoje = datas_unicas[0]
                self.dados_hoje = df[df['Timestamp'].dt.date == data_hoje].copy()
                logger.info(f"📊 Dados de hoje ({data_hoje}): {len(self.dados_hoje)} registros")
            else:
                logger.error("❌ Nenhum dado encontrado")
                return False
            
            if len(datas_unicas) >= 2:
                data_ontem = datas_unicas[1]
                self.dados_ontem = df[df['Timestamp'].dt.date == data_ontem].copy()
                logger.info(f"📊 Dados de ontem ({data_ontem}): {len(self.dados_ontem)} registros")
            else:
                logger.warning("⚠️ Apenas dados de hoje - sem comparação possível")
                self.dados_ontem = pd.DataFrame()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar dados: {e}")
            return False
    
    def detectar_mudancas_ofertas(self):
        """Detecta mudanças de ofertas entre ontem e hoje"""
        if self.dados_ontem.empty:
            logger.warning("⚠️ Sem dados de ontem - não é possível detectar mudanças")
            return {'ganharam_oferta': [], 'perderam_oferta': []}
        
        mudancas = {'ganharam_oferta': [], 'perderam_oferta': []}
        
        # Preparar dados considerando Parceiro + Moeda como chave única
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
            if chave in ontem_dict:
                hoje_data = hoje_dict[chave]
                ontem_data = ontem_dict[chave]
                
                # Ganhou oferta
                if hoje_data['oferta'] and not ontem_data['oferta']:
                    mudancas['ganharam_oferta'].append({
                        'parceiro': hoje_data['parceiro'],
                        'moeda': hoje_data['moeda'],
                        'pontos': hoje_data['pontos'],
                        'valor': hoje_data['valor'],
                        'chave': chave,
                        'pontos_por_moeda': hoje_data['pontos'] / hoje_data['valor'] if hoje_data['valor'] > 0 else 0
                    })
                
                # Perdeu oferta
                elif not hoje_data['oferta'] and ontem_data['oferta']:
                    mudancas['perderam_oferta'].append({
                        'parceiro': hoje_data['parceiro'],
                        'moeda': hoje_data['moeda'],
                        'pontos': hoje_data['pontos'],
                        'valor': hoje_data['valor'],
                        'chave': chave
                    })
        
        logger.info(f"🎯 Detectadas {len(mudancas['ganharam_oferta'])} novas ofertas")
        logger.info(f"📉 Detectadas {len(mudancas['perderam_oferta'])} ofertas finalizadas")
        
        return mudancas
    
    def carregar_usuarios_registrados(self):
        """Carrega tokens FCM dos usuários registrados"""
        if not os.path.exists(self.arquivo_tokens):
            # Criar arquivo exemplo
            exemplo = {
                "exemplo_user_1": {
                    "fcm_token": "EXEMPLO_TOKEN_FCM_AQUI_-_SUBSTITUA_PELO_TOKEN_REAL",
                    "favoritos": ["Netshoes|R$", "Magazine Luiza|R$", "Amazon|R$"],
                    "ativo": True,
                    "ultimo_acesso": datetime.now().isoformat(),
                    "configuracoes": {
                        "notificar_novas_ofertas": True,
                        "notificar_ofertas_perdidas": False,
                        "apenas_favoritos": True
                    }
                },
                "exemplo_user_2": {
                    "fcm_token": "OUTRO_EXEMPLO_TOKEN_FCM_AQUI",
                    "favoritos": ["Carrefour|R$", "Extra|R$"],
                    "ativo": False,
                    "ultimo_acesso": (datetime.now() - timedelta(days=7)).isoformat(),
                    "configuracoes": {
                        "notificar_novas_ofertas": True,
                        "notificar_ofertas_perdidas": True,
                        "apenas_favoritos": True
                    }
                }
            }
            
            try:
                with open(self.arquivo_tokens, 'w', encoding='utf-8') as f:
                    json.dump(exemplo, f, indent=2, ensure_ascii=False)
                logger.info(f"📄 Arquivo exemplo criado: {self.arquivo_tokens}")
                logger.info("💡 Edite o arquivo com tokens reais dos usuários")
            except Exception as e:
                logger.error(f"❌ Erro ao criar arquivo exemplo: {e}")
            
            return {}
        
        try:
            with open(self.arquivo_tokens, 'r', encoding='utf-8') as f:
                usuarios = json.load(f)
            
            # Filtrar apenas usuários ativos
            usuarios_ativos = {
                user_id: data for user_id, data in usuarios.items() 
                if data.get('ativo', False) and data.get('fcm_token', '').startswith(('EXEMPLO', 'OUTRO')) == False
            }
            
            logger.info(f"📱 {len(usuarios_ativos)} usuários ativos encontrados")
            return usuarios_ativos
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar tokens: {e}")
            return {}
    
    def enviar_notificacao_push(self, token, titulo, corpo, dados_extras=None):
        """Envia notificação push via Firebase FCM"""
        headers = {
            'Authorization': f'key={self.server_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        payload = {
            'to': token,
            'notification': {
                'title': titulo,
                'body': corpo,
                'icon': '/android-chrome-192x192.png',
                'badge': '/android-chrome-96x96.png',
                'click_action': 'https://gcaressato.github.io/livelo_scraper/',
                'tag': 'livelo-offer',
                'requireInteraction': True
            },
            'data': dados_extras or {},
            'webpush': {
                'headers': {
                    'Urgency': 'high',
                    'TTL': '86400'  # 24 horas
                },
                'notification': {
                    'icon': '/android-chrome-192x192.png',
                    'badge': '/android-chrome-96x96.png',
                    'requireInteraction': True,
                    'actions': [
                        {
                            'action': 'view_offer',
                            'title': '👀 Ver Oferta'
                        },
                        {
                            'action': 'dismiss', 
                            'title': '✖️ Dispensar'
                        }
                    ]
                }
            }
        }
        
        try:
            response = requests.post(
                self.fcm_url, 
                headers=headers, 
                json=payload, 
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success', 0) > 0:
                    logger.info(f"✅ Notificação enviada: {titulo[:50]}...")
                    return True
                else:
                    error_msg = result.get('results', [{}])[0].get('error', 'Erro desconhecido')
                    logger.error(f"❌ Falha no envio: {error_msg}")
                    
                    # Se token inválido, sugerir limpeza
                    if 'InvalidRegistration' in error_msg or 'NotRegistered' in error_msg:
                        logger.warning(f"⚠️ Token inválido - remover do arquivo: {token[:20]}...")
                    
                    return False
            else:
                logger.error(f"❌ Erro HTTP {response.status_code}: {response.text[:200]}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error("❌ Timeout na requisição FCM")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro na requisição: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Erro inesperado: {e}")
            return False
    
    def processar_notificacoes(self):
        """Processa e envia notificações para usuários relevantes"""
        logger.info("🔔 Processando notificações...")
        
        # Detectar mudanças
        mudancas = self.detectar_mudancas_ofertas()
        
        # Carregar usuários
        usuarios = self.carregar_usuarios_registrados()
        
        if not usuarios:
            logger.warning("⚠️ Nenhum usuário ativo registrado para notificações")
            return self._salvar_estatisticas(mudancas, 0, 0)
        
        notificacoes_enviadas = 0
        notificacoes_tentativas = 0
        
        for user_id, user_data in usuarios.items():
            try:
                token = user_data.get('fcm_token', '')
                favoritos = user_data.get('favoritos', [])
                config = user_data.get('configuracoes', {})
                
                if not token or not favoritos:
                    continue
                
                # Verificar configurações do usuário
                notificar_novas = config.get('notificar_novas_ofertas', True)
                apenas_favoritos = config.get('apenas_favoritos', True)
                
                if not notificar_novas:
                    continue
                
                # Encontrar ofertas relevantes para este usuário
                ofertas_relevantes = []
                
                for oferta in mudancas['ganharam_oferta']:
                    chave_oferta = oferta['chave']
                    
                    # Se apenas favoritos, verificar se está na lista
                    if apenas_favoritos and chave_oferta not in favoritos:
                        continue
                    
                    ofertas_relevantes.append(oferta)
                
                # Enviar notificação se houver ofertas relevantes
                if ofertas_relevantes:
                    notificacoes_tentativas += 1
                    
                    if len(ofertas_relevantes) == 1:
                        # Notificação para uma oferta
                        oferta = ofertas_relevantes[0]
                        titulo = f"🎯 {oferta['parceiro']} em oferta!"
                        corpo = f"{oferta['pontos_por_moeda']:.1f} pontos por {oferta['moeda']} - Aproveite!"
                        
                        dados_extras = {
                            'tipo': 'oferta_individual',
                            'parceiro': oferta['parceiro'],
                            'moeda': oferta['moeda'],
                            'pontos': str(oferta['pontos']),
                            'valor': str(oferta['valor']),
                            'url': 'https://gcaressato.github.io/livelo_scraper/'
                        }
                    else:
                        # Notificação para múltiplas ofertas
                        titulo = f"🔥 {len(ofertas_relevantes)} ofertas para você!"
                        
                        if len(ofertas_relevantes) <= 3:
                            parceiros = [o['parceiro'] for o in ofertas_relevantes]
                            corpo = f"{', '.join(parceiros)} - Confira no app!"
                        else:
                            primeiros = [o['parceiro'] for o in ofertas_relevantes[:2]]
                            corpo = f"{', '.join(primeiros)} e mais {len(ofertas_relevantes)-2} - Confira!"
                        
                        dados_extras = {
                            'tipo': 'ofertas_multiplas',
                            'total_ofertas': str(len(ofertas_relevantes)),
                            'parceiros': [o['parceiro'] for o in ofertas_relevantes],
                            'url': 'https://gcaressato.github.io/livelo_scraper/'
                        }
                    
                    # Tentar enviar
                    if self.enviar_notificacao_push(token, titulo, corpo, dados_extras):
                        notificacoes_enviadas += 1
                        logger.info(f"📱 Notificação enviada para {user_id}")
                    else:
                        logger.warning(f"⚠️ Falha ao enviar para {user_id}")
                
            except Exception as e:
                logger.error(f"❌ Erro ao processar usuário {user_id}: {e}")
                continue
        
        logger.info(f"🚀 Notificações enviadas: {notificacoes_enviadas}/{notificacoes_tentativas}")
        
        return self._salvar_estatisticas(mudancas, notificacoes_enviadas, notificacoes_tentativas)
    
    def _salvar_estatisticas(self, mudancas, enviadas, tentativas):
        """Salva estatísticas da execução"""
        stats = {
            'timestamp': datetime.now().isoformat(),
            'novas_ofertas': len(mudancas['ganharam_oferta']),
            'ofertas_finalizadas': len(mudancas['perderam_oferta']),
            'notificacoes_enviadas': enviadas,
            'notificacoes_tentativas': tentativas,
            'taxa_sucesso': f"{(enviadas/tentativas*100):.1f}%" if tentativas > 0 else "0%",
            'ofertas_detectadas': [
                {
                    'parceiro': o['parceiro'],
                    'moeda': o['moeda'],
                    'pontos_por_moeda': o['pontos_por_moeda']
                } for o in mudancas['ganharam_oferta']
            ]
        }
        
        try:
            with open(self.arquivo_stats, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            logger.info(f"📊 Estatísticas salvas em {self.arquivo_stats}")
        except Exception as e:
            logger.error(f"❌ Erro ao salvar estatísticas: {e}")
        
        return True
    
    def executar(self):
        """Executa o processo completo de notificações"""
        logger.info("🚀 Iniciando sistema de notificações Livelo Analytics")
        
        try:
            # 1. Carregar dados
            if not self.carregar_dados():
                logger.error("❌ Falha ao carregar dados - abortando")
                return False
            
            # 2. Processar notificações
            if not self.processar_notificacoes():
                logger.error("❌ Falha no processamento de notificações")
                return False
            
            logger.info("✅ Processo de notificações concluído")
            return True
            
        except KeyboardInterrupt:
            logger.info("⚠️ Processo interrompido pelo usuário")
            return False
        except Exception as e:
            logger.error(f"❌ Erro inesperado: {e}")
            return False

def main():
    """Função principal"""
    sender = LiveloNotificationSender()
    sucesso = sender.executar()
    
    if not sucesso:
        sys.exit(1)

if __name__ == "__main__":
    main()
