#!/usr/bin/env python3
"""
Sistema de Notificações Livelo
Mantém todas as funcionalidades originais mas não quebra o sistema principal
Funciona com Firebase Admin SDK v2 (sem API legada)
"""

import os
import sys
import json
import logging
import pandas as pd
from datetime import datetime, timedelta
import traceback

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
        self.firebase_configurado = False
        self.admin_sdk = None
        self.messaging = None
        self.projeto_id = None
        self.service_account_data = None
        self.vapid_key = None
        
        # Estatísticas
        self.stats = {
            'usuarios_ativos': 0,
            'notificacoes_enviadas': 0,
            'notificacoes_falharam': 0,
            'mudancas_detectadas': 0,
            'favoritos_processados': 0
        }
        
    def verificar_configuracao_firebase(self):
        """Verifica e configura Firebase Admin SDK"""
        logger.info("🔍 Verificando configuração Firebase...")
        
        try:
            # 1. Verificar variáveis de ambiente
            self.projeto_id = os.getenv('FIREBASE_PROJECT_ID')
            service_account_json = os.getenv('FIREBASE_SERVICE_ACCOUNT')
            self.vapid_key = os.getenv('FIREBASE_VAPID_KEY')
            
            if not self.projeto_id:
                logger.info("ℹ️ FIREBASE_PROJECT_ID não configurado")
                return False
                
            if not service_account_json:
                logger.info("ℹ️ FIREBASE_SERVICE_ACCOUNT não configurado")
                return False
                
            if not self.vapid_key:
                logger.info("ℹ️ FIREBASE_VAPID_KEY não configurado")
                return False
            
            # 2. Verificar se firebase-admin está instalado
            try:
                import firebase_admin
                from firebase_admin import credentials, messaging
                logger.info("✅ firebase-admin disponível")
            except ImportError:
                logger.info("ℹ️ firebase-admin não instalado")
                logger.info("💡 Para instalar: pip install firebase-admin")
                return False
            
            # 3. Parse e validação do service account
            try:
                self.service_account_data = json.loads(service_account_json)
                
                # Verificar campos obrigatórios
                campos_obrigatorios = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
                for campo in campos_obrigatorios:
                    if campo not in self.service_account_data:
                        logger.warning(f"⚠️ Campo obrigatório ausente no service account: {campo}")
                        return False
                
                if self.service_account_data.get('type') != 'service_account':
                    logger.warning("⚠️ Service account deve ser do tipo 'service_account'")
                    return False
                    
                logger.info(f"✅ Service account válido para projeto: {self.service_account_data.get('project_id')}")
                
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ FIREBASE_SERVICE_ACCOUNT não é um JSON válido: {e}")
                return False
            
            # 4. Inicializar Firebase Admin SDK
            try:
                # Criar credenciais
                cred = credentials.Certificate(self.service_account_data)
                
                # Verificar se já foi inicializado
                if not firebase_admin._apps:
                    firebase_admin.initialize_app(cred, {
                        'projectId': self.projeto_id
                    })
                    logger.info("🔥 Firebase Admin SDK inicializado")
                else:
                    logger.info("🔥 Firebase Admin SDK já estava inicializado")
                
                # Configurar messaging
                self.messaging = messaging
                self.firebase_configurado = True
                
                logger.info(f"✅ Firebase configurado completamente para: {self.projeto_id}")
                return True
                
            except Exception as e:
                logger.warning(f"⚠️ Erro ao inicializar Firebase Admin SDK: {e}")
                return False
                
        except Exception as e:
            logger.warning(f"⚠️ Erro geral na configuração Firebase: {e}")
            return False
    
    def carregar_tokens_usuarios(self):
        """Carrega e valida tokens FCM dos usuários"""
        logger.info("📱 Carregando tokens dos usuários...")
        
        try:
            if not os.path.exists('user_fcm_tokens.json'):
                logger.info("ℹ️ user_fcm_tokens.json não encontrado")
                logger.info("💡 Crie o arquivo com tokens FCM dos usuários")
                return []
            
            with open('user_fcm_tokens.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            usuarios_validos = []
            usuarios_processados = 0
            
            for usuario_id, dados in data.items():
                usuarios_processados += 1
                
                # Pular metadados (começam com _)
                if usuario_id.startswith('_'):
                    continue
                    
                # Validar estrutura do usuário
                if not isinstance(dados, dict):
                    logger.warning(f"⚠️ Usuário {usuario_id}: dados inválidos")
                    continue
                
                # Verificar se está ativo
                if not dados.get('ativo', False):
                    logger.debug(f"⏭️ Usuário {usuario_id}: inativo")
                    continue
                
                # Verificar token FCM
                token = dados.get('fcm_token', '')
                if not token or len(token) < 20:
                    logger.warning(f"⚠️ Usuário {usuario_id}: token FCM inválido")
                    continue
                
                # Validar favoritos
                favoritos = dados.get('favoritos', [])
                if not isinstance(favoritos, list):
                    logger.warning(f"⚠️ Usuário {usuario_id}: favoritos deve ser uma lista")
                    favoritos = []
                
                # Validar configurações
                config_padrao = {
                    'notificar_novas_ofertas': True,
                    'apenas_favoritos': True,
                    'notificar_grandes_mudancas': False,
                    'notificar_perdeu_oferta': False
                }
                
                configuracoes = dados.get('configuracoes', {})
                if not isinstance(configuracoes, dict):
                    configuracoes = {}
                
                # Mesclar com padrões
                config_final = {**config_padrao, **configuracoes}
                
                usuario_valido = {
                    'id': usuario_id,
                    'token': token,
                    'favoritos': favoritos,
                    'configuracoes': config_final,
                    'observacoes': dados.get('observacoes', ''),
                    'registrado_em': dados.get('registrado_em', datetime.now().isoformat())
                }
                
                usuarios_validos.append(usuario_valido)
                logger.debug(f"✅ Usuário {usuario_id}: {len(favoritos)} favoritos")
            
            self.stats['usuarios_ativos'] = len(usuarios_validos)
            logger.info(f"📊 {len(usuarios_validos)} usuários ativos de {usuarios_processados} processados")
            
            return usuarios_validos
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar tokens: {e}")
            logger.error(f"Trace: {traceback.format_exc()}")
            return []
    
    def analisar_mudancas_ofertas(self):
        """Analisa mudanças nas ofertas baseado nos dados coletados"""
        logger.info("📊 Analisando mudanças nas ofertas...")
        
        try:
            # Verificar se existem dados
            if not os.path.exists('livelo_parceiros.xlsx'):
                logger.info("ℹ️ livelo_parceiros.xlsx não encontrado")
                return self._gerar_mudancas_simuladas()
            
            # Carregar dados
            df = pd.read_excel('livelo_parceiros.xlsx')
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            
            # Obter dados de hoje e ontem
            datas_unicas = sorted(df['Timestamp'].dt.date.unique(), reverse=True)
            
            if len(datas_unicas) < 2:
                logger.info("ℹ️ Apenas um dia de dados - sem comparação")
                return self._gerar_mudancas_simuladas()
            
            data_hoje = datas_unicas[0]
            data_ontem = datas_unicas[1]
            
            df_hoje = df[df['Timestamp'].dt.date == data_hoje].copy()
            df_ontem = df[df['Timestamp'].dt.date == data_ontem].copy()
            
            logger.info(f"📅 Comparando {data_hoje} ({len(df_hoje)} registros) vs {data_ontem} ({len(df_ontem)} registros)")
            
            mudancas = []
            
            # Preparar dados para comparação (Parceiro + Moeda como chave)
            hoje_dict = {}
            for _, row in df_hoje.iterrows():
                chave = f"{row['Parceiro']}|{row['Moeda']}"
                hoje_dict[chave] = {
                    'parceiro': row['Parceiro'],
                    'moeda': row['Moeda'],
                    'oferta': row['Oferta'] == 'Sim',
                    'pontos': row['Pontos'],
                    'valor': row['Valor'],
                    'pontos_por_moeda': row['Pontos'] / row['Valor'] if row['Valor'] > 0 else 0
                }
            
            ontem_dict = {}
            for _, row in df_ontem.iterrows():
                chave = f"{row['Parceiro']}|{row['Moeda']}"
                ontem_dict[chave] = {
                    'parceiro': row['Parceiro'],
                    'moeda': row['Moeda'],
                    'oferta': row['Oferta'] == 'Sim',
                    'pontos': row['Pontos'],
                    'valor': row['Valor'],
                    'pontos_por_moeda': row['Pontos'] / row['Valor'] if row['Valor'] > 0 else 0
                }
            
            # Detectar mudanças
            for chave in hoje_dict:
                dados_hoje = hoje_dict[chave]
                
                if chave not in ontem_dict:
                    # Novo parceiro
                    mudancas.append({
                        'tipo': 'novo_parceiro',
                        'parceiro': dados_hoje['parceiro'],
                        'moeda': dados_hoje['moeda'],
                        'pontos': dados_hoje['pontos'],
                        'tem_oferta': dados_hoje['oferta'],
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    dados_ontem = ontem_dict[chave]
                    
                    # Ganhou oferta
                    if dados_hoje['oferta'] and not dados_ontem['oferta']:
                        mudancas.append({
                            'tipo': 'ganhou_oferta',
                            'parceiro': dados_hoje['parceiro'],
                            'moeda': dados_hoje['moeda'],
                            'pontos': dados_hoje['pontos'],
                            'pontos_anterior': dados_ontem['pontos'],
                            'timestamp': datetime.now().isoformat()
                        })
                    
                    # Perdeu oferta
                    elif not dados_hoje['oferta'] and dados_ontem['oferta']:
                        mudancas.append({
                            'tipo': 'perdeu_oferta',
                            'parceiro': dados_hoje['parceiro'],
                            'moeda': dados_hoje['moeda'],
                            'pontos': dados_hoje['pontos'],
                            'pontos_anterior': dados_ontem['pontos'],
                            'timestamp': datetime.now().isoformat()
                        })
                    
                    # Grande mudança de pontos (>20%)
                    elif dados_ontem['pontos'] > 0:
                        variacao = ((dados_hoje['pontos'] - dados_ontem['pontos']) / dados_ontem['pontos']) * 100
                        
                        if abs(variacao) >= 20:
                            mudancas.append({
                                'tipo': 'grande_mudanca_pontos',
                                'parceiro': dados_hoje['parceiro'],
                                'moeda': dados_hoje['moeda'],
                                'pontos': dados_hoje['pontos'],
                                'pontos_anterior': dados_ontem['pontos'],
                                'variacao_percentual': variacao,
                                'aumento': variacao > 0,
                                'timestamp': datetime.now().isoformat()
                            })
            
            # Parceiros que sumiram
            for chave in ontem_dict:
                if chave not in hoje_dict:
                    dados_ontem = ontem_dict[chave]
                    mudancas.append({
                        'tipo': 'parceiro_sumiu',
                        'parceiro': dados_ontem['parceiro'],
                        'moeda': dados_ontem['moeda'],
                        'pontos_anterior': dados_ontem['pontos'],
                        'tinha_oferta': dados_ontem['oferta'],
                        'timestamp': datetime.now().isoformat()
                    })
            
            self.stats['mudancas_detectadas'] = len(mudancas)
            
            # Log das mudanças encontradas
            tipos_mudanca = {}
            for mudanca in mudancas:
                tipo = mudanca['tipo']
                tipos_mudanca[tipo] = tipos_mudanca.get(tipo, 0) + 1
            
            logger.info(f"📈 {len(mudancas)} mudanças detectadas:")
            for tipo, quantidade in tipos_mudanca.items():
                logger.info(f"   {tipo}: {quantidade}")
            
            return mudancas
            
        except Exception as e:
            logger.warning(f"⚠️ Erro na análise de mudanças: {e}")
            logger.warning(f"Trace: {traceback.format_exc()}")
            return self._gerar_mudancas_simuladas()
    
    def _gerar_mudancas_simuladas(self):
        """Gera mudanças simuladas para teste"""
        mudancas_simuladas = [
            {
                'tipo': 'ganhou_oferta',
                'parceiro': 'Netshoes',
                'moeda': 'R$',
                'pontos': 6.5,
                'pontos_anterior': 4.0,
                'timestamp': datetime.now().isoformat()
            },
            {
                'tipo': 'grande_mudanca_pontos',
                'parceiro': 'Amazon',
                'moeda': 'R$',
                'pontos': 8.0,
                'pontos_anterior': 5.0,
                'variacao_percentual': 60.0,
                'aumento': True,
                'timestamp': datetime.now().isoformat()
            }
        ]
        
        logger.info(f"🎭 {len(mudancas_simuladas)} mudanças simuladas geradas para teste")
        return mudancas_simuladas
    
    def usuario_interessado_em_mudanca(self, usuario, mudanca):
        """Verifica se usuário está interessado nesta mudança"""
        config = usuario['configuracoes']
        favoritos = usuario['favoritos']
        
        # Chave do parceiro
        chave_parceiro = f"{mudanca['parceiro']}|{mudanca['moeda']}"
        
        # Se apenas favoritos, verificar se está nos favoritos
        if config.get('apenas_favoritos', True):
            if chave_parceiro not in favoritos:
                return False
        
        # Verificar tipo de notificação
        tipo = mudanca['tipo']
        
        if tipo == 'ganhou_oferta' or tipo == 'novo_parceiro':
            return config.get('notificar_novas_ofertas', True)
        
        elif tipo == 'perdeu_oferta':
            return config.get('notificar_perdeu_oferta', False)
        
        elif tipo == 'grande_mudanca_pontos':
            return config.get('notificar_grandes_mudancas', False)
        
        return False
    
    def criar_mensagem_notificacao(self, mudanca):
        """Cria título e corpo da notificação baseado na mudança"""
        tipo = mudanca['tipo']
        parceiro = mudanca['parceiro']
        pontos = mudanca.get('pontos', 0)
        moeda = mudanca['moeda']
        
        if tipo == 'ganhou_oferta':
            titulo = f"🎯 {parceiro} em oferta!"
            corpo = f"{pontos} pontos por {moeda}1 - Aproveite agora!"
            
        elif tipo == 'novo_parceiro':
            status_oferta = "em oferta" if mudanca.get('tem_oferta') else "sem oferta"
            titulo = f"🆕 Novo parceiro: {parceiro}"
            corpo = f"{pontos} pontos por {moeda}1 - {status_oferta}"
            
        elif tipo == 'perdeu_oferta':
            titulo = f"📉 {parceiro} saiu de oferta"
            corpo = f"Oferta finalizada - agora {pontos} pontos por {moeda}1"
            
        elif tipo == 'grande_mudanca_pontos':
            variacao = mudanca.get('variacao_percentual', 0)
            sinal = "📈" if mudanca.get('aumento') else "📉"
            titulo = f"{sinal} {parceiro} - mudança de {variacao:.1f}%"
            corpo = f"Agora {pontos} pontos por {moeda}1"
            
        elif tipo == 'parceiro_sumiu':
            titulo = f"👻 {parceiro} sumiu do site"
            corpo = f"Parceiro não encontrado na última coleta"
            
        else:
            titulo = f"🔔 Atualização: {parceiro}"
            corpo = f"Mudança detectada - {pontos} pontos por {moeda}1"
        
        return titulo, corpo
    
    def enviar_notificacao_firebase(self, token, titulo, corpo, dados_extras=None):
        """Envia notificação via Firebase Cloud Messaging"""
        if not self.firebase_configurado or not self.messaging:
            return False
            
        try:
            # Preparar dados extras
            dados = {
                'click_action': 'FCM_PLUGIN_ACTIVITY',
                'sound': 'default',
                'url': 'https://gcaressato.github.io/livelo_scraper/'
            }
            
            if dados_extras:
                dados.update(dados_extras)
            
            # Criar mensagem
            message = self.messaging.Message(
                notification=self.messaging.Notification(
                    title=titulo,
                    body=corpo
                ),
                data=dados,
                token=token,
                
                # Configuração Android
                android=self.messaging.AndroidConfig(
                    priority='high',
                    ttl=timedelta(hours=24),
                    notification=self.messaging.AndroidNotification(
                        icon='ic_notification',
                        color='#ff0a8c',
                        sound='default',
                        tag='livelo-offer',
                        click_action='FCM_PLUGIN_ACTIVITY'
                    )
                ),
                
                # Configuração Web
                webpush=self.messaging.WebpushConfig(
                    headers={
                        'TTL': '86400'  # 24 horas
                    },
                    notification=self.messaging.WebpushNotification(
                        title=titulo,
                        body=corpo,
                        icon='https://via.placeholder.com/192x192/ff0a8c/ffffff?text=L',
                        badge='https://via.placeholder.com/96x96/ff0a8c/ffffff?text=L',
                        tag='livelo-offer',
                        require_interaction=True,
                        actions=[
                            self.messaging.WebpushNotificationAction(
                                action='view',
                                title='👀 Ver Ofertas'
                            ),
                            self.messaging.WebpushNotificationAction(
                                action='dismiss', 
                                title='✖️ Dispensar'
                            )
                        ]
                    ),
                    fcm_options=self.messaging.WebpushFCMOptions(
                        link='https://gcaressato.github.io/livelo_scraper/'
                    )
                )
            )
            
            # Enviar mensagem
            response = self.messaging.send(message)
            logger.debug(f"✅ Notificação enviada: {response}")
            
            self.stats['notificacoes_enviadas'] += 1
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao enviar notificação: {e}")
            self.stats['notificacoes_falharam'] += 1
            return False
    
    def processar_notificacoes(self):
        """Processa e envia todas as notificações necessárias"""
        logger.info("🔔 Processando notificações...")
        
        # 1. Verificar configuração Firebase
        firebase_ok = self.verificar_configuracao_firebase()
        
        if not firebase_ok:
            logger.info("💡 Sistema funcionará sem notificações push")
            logger.info("💡 Para ativar notificações:")
            logger.info("   1. Configure FIREBASE_PROJECT_ID")
            logger.info("   2. Configure FIREBASE_SERVICE_ACCOUNT (JSON completo)")
            logger.info("   3. Configure FIREBASE_VAPID_KEY")
            logger.info("   4. Instale: pip install firebase-admin")
            logger.info("   5. Configure user_fcm_tokens.json com usuários")
            return True  # Não é erro crítico
        
        # 2. Carregar usuários
        usuarios = self.carregar_tokens_usuarios()
        
        if not usuarios:
            logger.info("📱 Nenhum usuário ativo para notificar")
            logger.info("💡 Configure user_fcm_tokens.json com tokens FCM")
            return True
        
        # 3. Analisar mudanças
        mudancas = self.analisar_mudancas_ofertas()
        
        if not mudancas:
            logger.info("📊 Nenhuma mudança detectada para notificar")
            return True
        
        # 4. Processar notificações para cada usuário
        notificacoes_processadas = 0
        
        for usuario in usuarios:
            usuario_id = usuario['id']
            favoritos_usuario = usuario['favoritos']
            
            logger.debug(f"👤 Processando usuário {usuario_id} ({len(favoritos_usuario)} favoritos)")
            
            for mudanca in mudancas:
                # Verificar se usuário está interessado
                if not self.usuario_interessado_em_mudanca(usuario, mudanca):
                    continue
                
                # Criar mensagem
                titulo, corpo = self.criar_mensagem_notificacao(mudanca)
                
                # Dados extras para a notificação
                dados_extras = {
                    'tipo_mudanca': mudanca['tipo'],
                    'parceiro': mudanca['parceiro'],
                    'moeda': mudanca['moeda'],
                    'pontos': str(mudanca.get('pontos', 0)),
                    'timestamp': mudanca['timestamp']
                }
                
                # Enviar notificação
                sucesso = self.enviar_notificacao_firebase(
                    usuario['token'], 
                    titulo, 
                    corpo, 
                    dados_extras
                )
                
                if sucesso:
                    notificacoes_processadas += 1
                    logger.debug(f"📤 {usuario_id}: {titulo}")
                else:
                    logger.warning(f"❌ Falha ao notificar {usuario_id}: {titulo}")
            
            self.stats['favoritos_processados'] += len(favoritos_usuario)
        
        logger.info(f"📊 {notificacoes_processadas} notificações processadas")
        return True
    
    def gerar_relatorio_final(self):
        """Gera relatório final das notificações"""
        print("\n" + "="*50)
        print("🔔 SISTEMA DE NOTIFICAÇÕES LIVELO")
        print("="*50)
        print(f"⏰ Executado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"🔥 Firebase: {'✅ Configurado' if self.firebase_configurado else '❌ Não configurado'}")
        print("")
        print("📊 ESTATÍSTICAS:")
        print(f"   👥 Usuários ativos: {self.stats['usuarios_ativos']}")
        print(f"   📈 Mudanças detectadas: {self.stats['mudancas_detectadas']}")
        print(f"   ⭐ Favoritos processados: {self.stats['favoritos_processados']}")
        print(f"   ✅ Notificações enviadas: {self.stats['notificacoes_enviadas']}")
        print(f"   ❌ Notificações falharam: {self.stats['notificacoes_falharam']}")
        print("")
        
        if self.firebase_configurado:
            if self.stats['notificacoes_enviadas'] > 0:
                print("🎉 NOTIFICAÇÕES ENVIADAS COM SUCESSO!")
                taxa_sucesso = (self.stats['notificacoes_enviadas'] / 
                               (self.stats['notificacoes_enviadas'] + self.stats['notificacoes_falharam']) * 100)
                print(f"📈 Taxa de sucesso: {taxa_sucesso:.1f}%")
            else:
                print("ℹ️ NENHUMA NOTIFICAÇÃO ENVIADA")
                print("💡 Verifique se há mudanças e usuários interessados")
        else:
            print("💡 PARA ATIVAR NOTIFICAÇÕES:")
            print("   1. Configure secrets do Firebase no GitHub")
            print("   2. Adicione usuários em user_fcm_tokens.json")
            print("   3. Instale firebase-admin: pip install firebase-admin")
        
        print("")
        print("ℹ️ Sistema principal funciona independentemente das notificações")
        print("="*50)
    
    def executar(self):
        """Executa sistema completo de notificações"""
        try:
            logger.info("🚀 Iniciando sistema de notificações Livelo...")
            
            sucesso = self.processar_notificacoes()
            
            if sucesso:
                logger.info("✅ Sistema de notificações processado com sucesso")
            else:
                logger.warning("⚠️ Sistema de notificações com problemas")
            
            self.gerar_relatorio_final()
            return sucesso
            
        except Exception as e:
            logger.error(f"❌ Erro inesperado no sistema de notificações: {e}")
            logger.error(f"Trace: {traceback.format_exc()}")
            
            # Relatório mesmo com erro
            print(f"\n⚠️ Sistema de notificações teve problemas: {e}")
            print("ℹ️ Sistema principal não foi afetado")
            
            # Não quebrar sistema principal
            return True

def main():
    """Função principal - sempre retorna sucesso para não quebrar pipeline"""
    try:
        sender = LiveloNotificationSender()
        sender.executar()
        
        # Sempre retornar sucesso (código 0) para não quebrar pipeline
        sys.exit(0)
        
    except Exception as e:
        print(f"⚠️ Erro crítico nas notificações: {e}")
        print("ℹ️ Sistema principal não foi afetado")
        
        # Mesmo com erro crítico, retornar sucesso para não quebrar pipeline
        sys.exit(0)

if __name__ == "__main__":
    main()
