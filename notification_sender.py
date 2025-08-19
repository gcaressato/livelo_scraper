#!/usr/bin/env python3
"""
Livelo Notification Sender - Sistema de Notificações Push Firebase
Versão corrigida para usar os secrets existentes (FIREBASE_SERVER_KEY)
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
        # Configurações do Firebase (via environment variables - SEUS SECRETS ATUAIS)
        self.project_id = os.getenv('FIREBASE_PROJECT_ID')
        self.server_key = os.getenv('FIREBASE_SERVER_KEY')
        
        # URLs do Firebase (Legacy API que funciona com SERVER_KEY)
        if self.server_key:
            self.fcm_url = "https://fcm.googleapis.com/fcm/send"
        else:
            self.fcm_url = None
        
        # Arquivos
        self.arquivo_dados = 'livelo_parceiros.xlsx'
        self.arquivo_tokens = 'user_fcm_tokens.json'
        
        # Status da inicialização
        self.firebase_disponivel = self._verificar_configuracao_firebase()
        
    def _verificar_configuracao_firebase(self):
        """Verifica se o Firebase está corretamente configurado"""
        if not self.project_id:
            logger.warning("⚠️ FIREBASE_PROJECT_ID não configurado")
            return False
            
        if not self.server_key:
            logger.warning("⚠️ FIREBASE_SERVER_KEY não configurado")
            return False
            
        # Verificar se server key tem tamanho mínimo
        if len(self.server_key) < 50:  # Server keys devem ser longas
            logger.warning(f"⚠️ FIREBASE_SERVER_KEY parece suspeita (tamanho: {len(self.server_key)})")
        
        logger.info(f"✅ Firebase configurado para projeto: {self.project_id}")
        logger.info(f"🔑 Server Key: ***{self.server_key[-10:] if len(self.server_key) > 10 else '***'}")
        return True
        
    def carregar_dados(self):
        """Carrega dados do Excel e separa por data"""
        try:
            if not os.path.exists(self.arquivo_dados):
                logger.error(f"❌ Arquivo {self.arquivo_dados} não encontrado")
                return False
                
            # Carregar dados
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
            logger.warning("⚠️ Sem dados anteriores - não é possível detectar mudanças")
            # Retornar todas as ofertas atuais como "novas" se for primeira execução
            mudancas = {'ganharam_oferta': [], 'perderam_oferta': []}
            
            ofertas_ativas = self.dados_hoje[self.dados_hoje['Oferta'] == 'Sim']
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
            
            logger.info(f"🎯 Primeira execução - {len(mudancas['ganharam_oferta'])} ofertas ativas encontradas")
            return mudancas
        
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
            hoje_data = hoje_dict[chave]
            
            if chave in ontem_dict:
                ontem_data = ontem_dict[chave]
                
                # Ganhou oferta
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
                
                # Perdeu oferta
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
                # Novo parceiro/moeda com oferta
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
            # Criar arquivo exemplo
            exemplo = {
                "exemplo_user_1": {
                    "fcm_token": "EXEMPLO_TOKEN_FCM_AQUI_-_SUBSTITUA_PELO_TOKEN_REAL",
                    "favoritos": ["Netshoes|R$", "Magazine Luiza|R$", "Amazon|R$"],
                    "ativo": False,  # Marcado como inativo por ser exemplo
                    "ultimo_acesso": datetime.now().isoformat(),
                    "configuracoes": {
                        "notificar_novas_ofertas": True,
                        "notificar_ofertas_perdidas": False,
                        "apenas_favoritos": True,
                        "horario_silencioso_inicio": "23:00",
                        "horario_silencioso_fim": "07:00"
                    },
                    "observacoes": "ESTE É UM EXEMPLO - Configure tokens reais de usuários"
                },
                "exemplo_user_2": {
                    "fcm_token": "OUTRO_EXEMPLO_TOKEN_FCM_AQUI",
                    "favoritos": ["Carrefour|R$", "Extra|R$"],
                    "ativo": False,  # Marcado como inativo por ser exemplo
                    "ultimo_acesso": (datetime.now() - timedelta(days=7)).isoformat(),
                    "configuracoes": {
                        "notificar_novas_ofertas": True,
                        "notificar_ofertas_perdidas": True,
                        "apenas_favoritos": False
                    },
                    "observacoes": "EXEMPLO - Token de teste"
                }
            }
            
            try:
                with open(self.arquivo_tokens, 'w', encoding='utf-8') as f:
                    json.dump(exemplo, f, indent=2, ensure_ascii=False)
                logger.info(f"📄 Arquivo exemplo criado: {self.arquivo_tokens}")
                logger.info("💡 Para ativar notificações:")
                logger.info("   1. Edite o arquivo com tokens reais dos usuários")
                logger.info("   2. Mude 'ativo' para true")
                logger.info("   3. Configure os favoritos de cada usuário")
            except Exception as e:
                logger.error(f"❌ Erro ao criar arquivo exemplo: {e}")
            
            return {}
        
        try:
            with open(self.arquivo_tokens, 'r', encoding='utf-8') as f:
                usuarios = json.load(f)
            
            # Filtrar apenas usuários ativos com tokens válidos
            usuarios_ativos = {}
            for user_id, data in usuarios.items():
                if not data.get('ativo', False):
                    continue
                    
                token = data.get('fcm_token', '')
                if not token or token.startswith(('EXEMPLO', 'OUTRO')):
                    continue
                    
                # Token deve ter tamanho mínimo (FCM tokens são longos)
                if len(token) < 100:
                    logger.warning(f"⚠️ Token suspeito para {user_id}: muito curto")
                    continue
                    
                usuarios_ativos[user_id] = data
            
            logger.info(f"📱 {len(usuarios_ativos)} usuários ativos com tokens válidos")
            return usuarios_ativos
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar tokens: {e}")
            return {}
    
    def enviar_notificacao_push(self, token, titulo, corpo, dados_extras=None):
        """Envia notificação push via Firebase FCM Legacy API"""
        if not self.firebase_disponivel:
            logger.warning("⚠️ Firebase não configurado - pulando notificação")
            return False
            
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
                'icon': 'https://via.placeholder.com/192x192/ff0a8c/ffffff?text=L',
                'badge': 'https://via.placeholder.com/96x96/ff0a8c/ffffff?text=L',
                'click_action': 'https://livel-analytics.web.app/',
                'tag': 'livelo-offer',
                'requireInteraction': True
            },
            'data': dados_extras or {
                'timestamp': datetime.now().isoformat(),
                'source': 'livelo-analytics'
            },
            'webpush': {
                'headers': {
                    'Urgency': 'high',
                    'TTL': '86400'  # 24 horas
                },
                'notification': {
                    'icon': 'https://via.placeholder.com/192x192/ff0a8c/ffffff?text=L',
                    'badge': 'https://via.placeholder.com/96x96/ff0a8c/ffffff?text=L',
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
                    error_result = result.get('results', [{}])[0]
                    error_msg = error_result.get('error', 'Erro desconhecido')
                    logger.error(f"❌ Falha no envio FCM: {error_msg}")
                    
                    # Classificar tipos de erro
                    if error_msg in ['InvalidRegistration', 'NotRegistered']:
                        logger.warning(f"⚠️ Token inválido - considere remover: {token[:20]}...")
                    elif error_msg == 'MessageTooBig':
                        logger.warning("⚠️ Mensagem muito grande")
                    elif error_msg == 'InvalidTtl':
                        logger.warning("⚠️ TTL inválido")
                    
                    return False
            else:
                logger.error(f"❌ Erro HTTP {response.status_code}: {response.text[:200]}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error("❌ Timeout na requisição FCM (30s)")
            return False
        except requests.exceptions.ConnectionError:
            logger.error("❌ Erro de conexão com FCM")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro na requisição FCM: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Erro inesperado no envio: {e}")
            return False
    
    def processar_notificacoes(self):
        """Processa e envia notificações para usuários relevantes"""
        logger.info("🔔 Processando notificações...")
        
        # Detectar mudanças
        mudancas = self.detectar_mudancas_ofertas()
        
        # Se não há mudanças, não enviar notificações
        if not mudancas['ganharam_oferta'] and not mudancas['perderam_oferta']:
            logger.info("ℹ️ Nenhuma mudança detectada - não há notificações para enviar")
            return self._imprimir_estatisticas(mudancas, 0, 0)
        
        # Carregar usuários
        usuarios = self.carregar_usuarios_registrados()
        
        if not usuarios:
            logger.warning("⚠️ Nenhum usuário ativo registrado para notificações")
            return self._imprimir_estatisticas(mudancas, 0, 0)
        
        if not self.firebase_disponivel:
            logger.warning("⚠️ Firebase não configurado - simulando envio de notificações")
            return self._imprimir_estatisticas(mudancas, 0, len(usuarios))
        
        notificacoes_enviadas = 0
        notificacoes_tentativas = 0
        
        for user_id, user_data in usuarios.items():
            try:
                token = user_data.get('fcm_token', '')
                favoritos = user_data.get('favoritos', [])
                config = user_data.get('configuracoes', {})
                
                if not token:
                    logger.warning(f"⚠️ Token ausente para {user_id}")
                    continue
                
                # Verificar configurações do usuário
                notificar_novas = config.get('notificar_novas_ofertas', True)
                apenas_favoritos = config.get('apenas_favoritos', True)
                
                if not notificar_novas:
                    logger.debug(f"📵 {user_id} tem notificações desabilitadas")
                    continue
                
                # Encontrar ofertas relevantes para este usuário
                ofertas_relevantes = []
                
                for oferta in mudancas['ganharam_oferta']:
                    chave_oferta = oferta['chave']
                    
                    # Se apenas favoritos, verificar se está na lista
                    if apenas_favoritos:
                        if not favoritos or chave_oferta not in favoritos:
                            continue
                    
                    ofertas_relevantes.append(oferta)
                
                # Enviar notificação se houver ofertas relevantes
                if ofertas_relevantes:
                    notificacoes_tentativas += 1
                    
                    # Evitar spam em primeira execução
                    if ofertas_relevantes[0].get('primeira_execucao') and len(ofertas_relevantes) > 5:
                        # Notificação resumida para primeira execução com muitas ofertas
                        titulo = f"🎯 Livelo Analytics Ativo!"
                        corpo = f"{len(ofertas_relevantes)} ofertas encontradas nos seus favoritos"
                        
                        dados_extras = {
                            'tipo': 'primeira_execucao',
                            'total_ofertas': str(len(ofertas_relevantes)),
                            'url': 'https://livel-analytics.web.app/',
                            'timestamp': datetime.now().isoformat()
                        }
                    elif len(ofertas_relevantes) == 1:
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
                            'url': 'https://livel-analytics.web.app/',
                            'timestamp': datetime.now().isoformat()
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
                            'parceiros': [o['parceiro'] for o in ofertas_relevantes[:5]],  # Limitado para não exceder tamanho
                            'url': 'https://livel-analytics.web.app/',
                            'timestamp': datetime.now().isoformat()
                        }
                    
                    # Tentar enviar
                    if self.enviar_notificacao_push(token, titulo, corpo, dados_extras):
                        notificacoes_enviadas += 1
                        logger.info(f"📱 Notificação enviada para {user_id}: {len(ofertas_relevantes)} ofertas")
                    else:
                        logger.warning(f"⚠️ Falha ao enviar para {user_id}")
                else:
                    logger.debug(f"📭 Nenhuma oferta relevante para {user_id}")
                
            except Exception as e:
                logger.error(f"❌ Erro ao processar usuário {user_id}: {e}")
                continue
        
        logger.info(f"🚀 Notificações: {notificacoes_enviadas} enviadas / {notificacoes_tentativas} tentativas")
        
        return self._imprimir_estatisticas(mudancas, notificacoes_enviadas, notificacoes_tentativas)
    
    def _imprimir_estatisticas(self, mudancas, enviadas, tentativas):
        """Imprime estatísticas no console ao invés de salvar arquivo"""
        print("\n" + "="*60)
        print("📊 RELATÓRIO DE NOTIFICAÇÕES LIVELO ANALYTICS")
        print("="*60)
        print(f"⏰ Timestamp: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"🔥 Firebase: {'✅ Legacy API Ativo' if self.firebase_disponivel else '❌ Desabilitado'}")
        print(f"📁 Dados: {'✅ ' + self.arquivo_dados if os.path.exists(self.arquivo_dados) else '❌ Ausente'}")
        print(f"👥 Tokens: {'✅ ' + self.arquivo_tokens if os.path.exists(self.arquivo_tokens) else '❌ Ausente'}")
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
            print("🎯 NOVAS OFERTAS DETECTADAS:")
            for i, oferta in enumerate(mudancas['ganharam_oferta'][:10], 1):  # Mostrar até 10
                pontos_por_moeda = oferta['pontos_por_moeda']
                primeira = " (🆕 PRIMEIRA EXECUÇÃO)" if oferta.get('primeira_execucao') else ""
                print(f"   {i:2d}. {oferta['parceiro']} | {oferta['moeda']} - {pontos_por_moeda:.1f} pts{primeira}")
            
            if len(mudancas['ganharam_oferta']) > 10:
                print(f"   ... e mais {len(mudancas['ganharam_oferta'])-10} ofertas")
        
        if mudancas['perderam_oferta']:
            print("")
            print("📉 OFERTAS FINALIZADAS:")
            for i, oferta in enumerate(mudancas['perderam_oferta'][:5], 1):  # Mostrar até 5
                print(f"   {i}. {oferta['parceiro']} | {oferta['moeda']}")
        
        print("="*60)
        
        return True
    
    def executar(self):
        """Executa o processo completo de notificações"""
        print("\n🚀 INICIANDO SISTEMA DE NOTIFICAÇÕES LIVELO ANALYTICS")
        print("="*60)
        
        # Mostrar configuração
        print("🔧 CONFIGURAÇÃO:")
        print(f"   📊 Projeto Firebase: {self.project_id or 'NÃO CONFIGURADO'}")
        print(f"   🔑 Server Key: {'✅ Configurado' if self.server_key else '❌ Ausente'}")
        print(f"   🔥 Firebase: {'✅ Legacy API Disponível' if self.firebase_disponivel else '❌ Indisponível'}")
        print(f"   📁 Diretório: {os.getcwd()}")
        
        try:
            # 1. Carregar dados
            if not self.carregar_dados():
                logger.error("❌ Falha ao carregar dados - abortando")
                return False
            
            # 2. Processar notificações
            if not self.processar_notificacoes():
                logger.error("❌ Falha no processamento de notificações")
                return False
            
            print("\n✅ PROCESSO DE NOTIFICAÇÕES CONCLUÍDO")
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
    
    sys.exit(0 if sucesso else 1)

if __name__ == "__main__":
    main()
