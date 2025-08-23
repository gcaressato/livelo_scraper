#!/usr/bin/env python3
"""
Sistema de Notificações Firebase para Livelo Analytics - GitHub Actions
VERSÃO 2.0 - Com Firestore integrado diretamente
100% opcional - nunca quebra o pipeline principal
"""

import os
import sys
import json
import logging
import pandas as pd
from datetime import datetime, timedelta
import traceback

# CONFIGURAR CAMINHOS GLOBAIS PARA GITHUB ACTIONS
script_dir = os.path.dirname(os.path.abspath(__file__))
print(f"Script executando em: {script_dir}")

# Configurar logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(script_dir, 'firebase_notifications.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LiveloFirebaseNotifier:
    def __init__(self):
        self.firebase_configurado = False
        self.messaging = None
        self.firestore_db = None
        self.projeto_id = None
        self.script_dir = script_dir
        
        # Estatísticas
        self.stats = {
            'usuarios_ativos': 0,
            'usuarios_firestore': 0,
            'usuarios_json': 0,
            'notificacoes_enviadas': 0,
            'notificacoes_falharam': 0,
            'mudancas_detectadas': 0,
            'favoritos_processados': 0
        }
        
    def verificar_configuracao_firebase(self):
        """Verifica e configura Firebase Admin SDK v2 + Firestore"""
        logger.info("Verificando configuração Firebase...")
        
        try:
            # 1. Verificar variáveis de ambiente
            self.projeto_id = os.getenv('FIREBASE_PROJECT_ID')
            service_account_json = os.getenv('FIREBASE_SERVICE_ACCOUNT')
            
            if not self.projeto_id:
                logger.info("FIREBASE_PROJECT_ID não configurado")
                return False
                
            if not service_account_json:
                logger.info("FIREBASE_SERVICE_ACCOUNT não configurado")
                return False
            
            # 2. Verificar se firebase-admin está instalado
            try:
                import firebase_admin
                from firebase_admin import credentials, messaging, firestore
                logger.info("firebase-admin disponível")
            except ImportError:
                logger.info("firebase-admin não instalado")
                logger.info("Para instalar: pip install firebase-admin")
                return False
            
            # 3. Parse e validação do service account
            try:
                service_account_data = json.loads(service_account_json)
                
                # Verificar campos obrigatórios
                campos_obrigatorios = ['type', 'project_id', 'private_key', 'client_email']
                for campo in campos_obrigatorios:
                    if campo not in service_account_data:
                        logger.warning(f"Campo obrigatório ausente: {campo}")
                        return False
                
                logger.info(f"Service account válido para projeto: {service_account_data.get('project_id')}")
                
            except json.JSONDecodeError as e:
                logger.warning(f"FIREBASE_SERVICE_ACCOUNT não é um JSON válido: {e}")
                return False
            
            # 4. Inicializar Firebase Admin SDK v2
            try:
                # Criar credenciais
                cred = credentials.Certificate(service_account_data)
                
                # Verificar se já foi inicializado
                if not firebase_admin._apps:
                    firebase_admin.initialize_app(cred, {
                        'projectId': self.projeto_id
                    })
                    logger.info("Firebase Admin SDK inicializado")
                else:
                    logger.info("Firebase Admin SDK já estava inicializado")
                
                # Configurar messaging E firestore
                self.messaging = messaging
                self.firestore_db = firestore.client()
                self.firebase_configurado = True
                
                logger.info(f"Firebase + Firestore configurados para: {self.projeto_id}")
                return True
                
            except Exception as e:
                logger.warning(f"Erro ao inicializar Firebase: {e}")
                return False
                
        except Exception as e:
            logger.warning(f"Erro na configuração Firebase: {e}")
            return False
    
    def carregar_usuarios_firestore(self):
        """Carrega usuários do Firestore"""
        if not self.firestore_db:
            logger.warning("Firestore não configurado")
            return {}
            
        try:
            logger.info("Carregando usuários do Firestore...")
            usuarios_ref = self.firestore_db.collection('usuarios')
            docs = usuarios_ref.stream()
            
            usuarios = {}
            for doc in docs:
                try:
                    data = doc.to_dict()
                    user_id = doc.id
                    
                    # Converter formato Firestore para formato esperado
                    usuario_convertido = {
                        "fcm_token": data.get('fcm_token', ''),
                        "favoritos": data.get('favoritos', []),
                        "configuracoes": data.get('configuracoes', {
                            "notificar_ofertas": True,
                            "notificar_mudancas": True,
                            "apenas_favoritos": True
                        }),
                        "ativo": data.get('ativo', True),
                        "nome": data.get('nome', f'Usuário {user_id}'),
                        "fonte": "firestore",
                        "updated_at": data.get('updated_at'),
                        "created_at": data.get('created_at')
                    }
                    
                    usuarios[user_id] = usuario_convertido
                    
                except Exception as e:
                    logger.warning(f"Erro ao processar usuário {doc.id}: {e}")
                    continue
            
            self.stats['usuarios_firestore'] = len(usuarios)
            logger.info(f"✅ Carregados {len(usuarios)} usuários do Firestore")
            return usuarios
            
        except Exception as e:
            logger.warning(f"Erro ao carregar usuários do Firestore: {e}")
            return {}
    
    def carregar_usuarios_json(self):
        """Carrega usuários do arquivo JSON (fallback)"""
        arquivo_usuarios = os.path.join(self.script_dir, 'usuarios_favoritos.json')
        
        # Usuários de exemplo
        usuarios_exemplo = {
            "user_demo_1": {
                "fcm_token": "exemplo_token_demo_1",
                "favoritos": ["Netshoes|R$", "Amazon|R$", "Magazine Luiza|R$"],
                "configuracoes": {
                    "notificar_ofertas": True,
                    "notificar_mudancas": True,
                    "apenas_favoritos": True
                },
                "ativo": True,
                "nome": "Usuário Demo 1",
                "fonte": "json"
            },
            "user_demo_2": {
                "fcm_token": "exemplo_token_demo_2", 
                "favoritos": ["Submarino|R$", "Americanas|R$"],
                "configuracoes": {
                    "notificar_ofertas": True,
                    "notificar_mudancas": False,
                    "apenas_favoritos": True
                },
                "ativo": True,
                "nome": "Usuário Demo 2",
                "fonte": "json"
            }
        }
        
        # Tentar carregar do arquivo
        try:
            if os.path.exists(arquivo_usuarios):
                with open(arquivo_usuarios, 'r', encoding='utf-8') as f:
                    usuarios_data = json.load(f)
                    # Marcar fonte como JSON
                    for user_id in usuarios_data:
                        usuarios_data[user_id]['fonte'] = 'json'
                    
                    self.stats['usuarios_json'] = len(usuarios_data)
                    logger.info(f"✅ Carregados {len(usuarios_data)} usuários do JSON")
                    return usuarios_data
            else:
                logger.info(f"Arquivo JSON não encontrado: {arquivo_usuarios}")
                logger.info("Usando dados de exemplo para demonstração")
                
                # Salvar exemplo para referência
                arquivo_exemplo = os.path.join(self.script_dir, 'usuarios_favoritos_exemplo.json')
                try:
                    with open(arquivo_exemplo, 'w', encoding='utf-8') as f:
                        json.dump(usuarios_exemplo, f, indent=2, ensure_ascii=False)
                    logger.info(f"Arquivo de exemplo criado: {arquivo_exemplo}")
                except Exception as e:
                    logger.warning(f"Erro ao criar arquivo de exemplo: {e}")
                
                self.stats['usuarios_json'] = len(usuarios_exemplo)
                return usuarios_exemplo
                
        except Exception as e:
            logger.warning(f"Erro ao carregar usuários do JSON: {e}")
            self.stats['usuarios_json'] = len(usuarios_exemplo)
            return usuarios_exemplo
    
    def carregar_usuarios_favoritos(self):
        """Carrega usuários de AMBAS as fontes: Firestore (prioridade) + JSON (fallback)"""
        logger.info("Carregando usuários com favoritos (Firestore + JSON)...")
        
        usuarios_final = {}
        
        # 1. Tentar carregar do Firestore primeiro (se Firebase estiver configurado)
        if self.firebase_configurado and self.firestore_db:
            usuarios_firestore = self.carregar_usuarios_firestore()
            usuarios_final.update(usuarios_firestore)
            logger.info(f"Firestore: {len(usuarios_firestore)} usuários carregados")
        
        # 2. Carregar do JSON como fallback ou complemento
        usuarios_json = self.carregar_usuarios_json()
        
        # Adicionar usuários do JSON que não existem no Firestore
        for user_id, user_data in usuarios_json.items():
            if user_id not in usuarios_final:
                usuarios_final[user_id] = user_data
                logger.debug(f"Adicionado usuário do JSON: {user_id}")
        
        logger.info(f"JSON: {len(usuarios_json)} usuários disponíveis")
        
        # 3. Se não tem usuários, usar exemplo
        if not usuarios_final:
            logger.warning("Nenhum usuário encontrado em nenhuma fonte!")
            usuarios_final = self.carregar_usuarios_json()
        
        total_usuarios = len(usuarios_final)
        firestore_count = len([u for u in usuarios_final.values() if u.get('fonte') == 'firestore'])
        json_count = len([u for u in usuarios_final.values() if u.get('fonte') == 'json'])
        
        logger.info(f"📊 RESUMO USUÁRIOS:")
        logger.info(f"   🔥 Firestore: {firestore_count} usuários")
        logger.info(f"   📄 JSON: {json_count} usuários")
        logger.info(f"   📋 Total final: {total_usuarios} usuários")
        
        return usuarios_final
    
    def analisar_mudancas_ofertas(self):
        """Analisa mudanças nas ofertas baseado nos dados do scraper com caminhos corretos"""
        logger.info("Analisando mudanças nas ofertas...")
        
        try:
            # Arquivo Excel com caminho absoluto
            arquivo_excel = os.path.join(self.script_dir, 'livelo_parceiros.xlsx')
            
            # Verificar se existem dados
            if not os.path.exists(arquivo_excel):
                logger.info(f"Arquivo não encontrado: {arquivo_excel}")
                return self._gerar_mudancas_demo()
            
            # Carregar dados
            df = pd.read_excel(arquivo_excel)
            logger.info(f"Dados carregados: {len(df)} registros")
            
            # Converter timestamp para datetime se necessário
            if 'Timestamp' in df.columns:
                df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            
            # Analisar mudanças reais
            mudancas = []
            
            # Exemplo: detectar ofertas baseado em dados
            if 'Oferta' in df.columns:
                ofertas = df[df['Oferta'] == 'Sim']
                
                for _, row in ofertas.iterrows():
                    mudancas.append({
                        'tipo': 'nova_oferta',
                        'parceiro': row.get('Parceiro', 'Parceiro Desconhecido'),
                        'moeda': row.get('Moeda', 'R$'),
                        'pontos': row.get('Pontos', 0),
                        'categoria': row.get('Categoria', 'Geral'),
                        'timestamp': datetime.now().isoformat()
                    })
            
            # Se não há mudanças reais, usar demo
            if not mudancas:
                mudancas = self._gerar_mudancas_demo()
            
            self.stats['mudancas_detectadas'] = len(mudancas)
            logger.info(f"{len(mudancas)} mudanças detectadas")
            
            return mudancas
            
        except Exception as e:
            logger.warning(f"Erro na análise de mudanças: {e}")
            logger.warning(f"Trace: {traceback.format_exc()}")
            return self._gerar_mudancas_demo()
    
    def _gerar_mudancas_demo(self):
        """Gera mudanças demonstrativas para teste"""
        mudancas_demo = [
            {
                'tipo': 'nova_oferta',
                'parceiro': 'Netshoes',
                'moeda': 'R$',
                'pontos': 6.5,
                'categoria': 'Esportes',
                'timestamp': datetime.now().isoformat()
            },
            {
                'tipo': 'mudanca_pontos',
                'parceiro': 'Amazon',
                'moeda': 'R$',
                'pontos': 8.0,
                'pontos_anterior': 5.0,
                'categoria': 'E-commerce',
                'timestamp': datetime.now().isoformat()
            }
        ]
        
        logger.info(f"{len(mudancas_demo)} mudanças demo geradas")
        return mudancas_demo
    
    def usuario_interessado(self, usuario, mudanca):
        """Verifica se usuário está interessado na mudança"""
        favoritos = usuario.get('favoritos', [])
        config = usuario.get('configuracoes', {})
        
        # Chave do parceiro (Parceiro|Moeda)
        chave_parceiro = f"{mudanca['parceiro']}|{mudanca['moeda']}"
        
        # Se configurado para apenas favoritos
        if config.get('apenas_favoritos', True):
            if chave_parceiro not in favoritos:
                return False
        
        # Verificar tipo de notificação
        if mudanca['tipo'] == 'nova_oferta':
            return config.get('notificar_ofertas', True)
        elif mudanca['tipo'] == 'mudanca_pontos':
            return config.get('notificar_mudancas', True)
        
        return True
    
    def criar_mensagem(self, mudanca):
        """Cria título e corpo da notificação"""
        tipo = mudanca['tipo']
        parceiro = mudanca['parceiro']
        pontos = mudanca.get('pontos', 0)
        
        if tipo == 'nova_oferta':
            titulo = f"🎯 {parceiro} em oferta!"
            corpo = f"{pontos} pontos por R$1 - Aproveite agora!"
            
        elif tipo == 'mudanca_pontos':
            pontos_anterior = mudanca.get('pontos_anterior', 0)
            if pontos > pontos_anterior:
                titulo = f"📈 {parceiro} - Pontos aumentaram!"
                corpo = f"De {pontos_anterior} para {pontos} pontos por R$1"
            else:
                titulo = f"📉 {parceiro} - Pontos diminuíram"
                corpo = f"De {pontos_anterior} para {pontos} pontos por R$1"
        else:
            titulo = f"🔔 {parceiro} - Atualização"
            corpo = f"Nova informação sobre {parceiro}"
        
        return titulo, corpo
    
    def enviar_notificacao(self, token, titulo, corpo, dados_extras=None):
        """Envia notificação via Firebase Cloud Messaging v2"""
        if not self.firebase_configurado or not self.messaging:
            return False
            
        try:
            # Preparar dados extras
            dados = {
                'click_action': 'FLUTTER_NOTIFICATION_CLICK',
                'url': 'https://livel-analytics.web.app/',
                'sound': 'default'
            }
            
            if dados_extras:
                dados.update(dados_extras)
            
            # Criar mensagem (Firebase Admin SDK v2)
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
                    ttl=timedelta(hours=1),
                    notification=self.messaging.AndroidNotification(
                        icon='ic_notification',
                        color='#ff0a8c',
                        sound='default',
                        click_action='FLUTTER_NOTIFICATION_CLICK'
                    )
                ),
                
                # Configuração Web
                webpush=self.messaging.WebpushConfig(
                    notification=self.messaging.WebpushNotification(
                        title=titulo,
                        body=corpo,
                        icon='https://livel-analytics.web.app/icon-192.png',
                        click_action='https://livel-analytics.web.app/'
                    )
                )
            )
            
            # Enviar mensagem
            response = self.messaging.send(message)
            logger.debug(f"Notificação enviada: {response}")
            
            self.stats['notificacoes_enviadas'] += 1
            return True
            
        except Exception as e:
            logger.warning(f"Erro ao enviar notificação: {e}")
            self.stats['notificacoes_falharam'] += 1
            return False
    
    def processar_notificacoes(self):
        """Processa todas as notificações"""
        logger.info("Processando notificações...")
        
        # 1. Verificar Firebase
        if not self.verificar_configuracao_firebase():
            logger.info("Firebase não configurado - sistema funcionará sem notificações")
            return True
        
        # 2. Carregar usuários (Firestore + JSON)
        usuarios = self.carregar_usuarios_favoritos()
        usuarios_ativos = {k: v for k, v in usuarios.items() if v.get('ativo', False)}
        
        self.stats['usuarios_ativos'] = len(usuarios_ativos)
        
        if not usuarios_ativos:
            logger.info("Nenhum usuário ativo para notificar")
            return True
        
        # 3. Analisar mudanças
        mudancas = self.analisar_mudancas_ofertas()
        
        if not mudancas:
            logger.info("Nenhuma mudança detectada")
            return True
        
        # 4. Enviar notificações
        for user_id, usuario in usuarios_ativos.items():
            token = usuario.get('fcm_token')
            if not token or token.startswith('exemplo_'):
                logger.debug(f"Token inválido ou de exemplo para {user_id}, pulando")
                continue
                
            favoritos = usuario.get('favoritos', [])
            self.stats['favoritos_processados'] += len(favoritos)
            
            for mudanca in mudancas:
                if self.usuario_interessado(usuario, mudanca):
                    titulo, corpo = self.criar_mensagem(mudanca)
                    
                    dados_extras = {
                        'tipo': mudanca['tipo'],
                        'parceiro': mudanca['parceiro'],
                        'pontos': str(mudanca.get('pontos', 0))
                    }
                    
                    sucesso = self.enviar_notificacao(token, titulo, corpo, dados_extras)
                    
                    if sucesso:
                        logger.info(f"✅ Notificação enviada para {user_id}: {titulo}")
                    else:
                        logger.warning(f"❌ Falha ao notificar {user_id}")
        
        return True
    
    def gerar_relatorio(self):
        """Gera relatório das notificações"""
        print("\n" + "="*70)
        print("🔔 SISTEMA DE NOTIFICAÇÕES FIREBASE + FIRESTORE")
        print("="*70)
        print(f"⏰ Executado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"📁 Diretório: {self.script_dir}")
        print(f"🔥 Firebase: {'✅ Configurado' if self.firebase_configurado else '❌ Não configurado'}")
        print(f"🗃️ Firestore: {'✅ Ativo' if self.firestore_db else '❌ Não disponível'}")
        print("")
        print("📊 ESTATÍSTICAS DE USUÁRIOS:")
        print(f"   🔥 Firestore: {self.stats['usuarios_firestore']} usuários")
        print(f"   📄 JSON: {self.stats['usuarios_json']} usuários")
        print(f"   👥 Ativos: {self.stats['usuarios_ativos']} usuários")
        print("")
        print("📊 ESTATÍSTICAS DE NOTIFICAÇÕES:")
        print(f"   📈 Mudanças detectadas: {self.stats['mudancas_detectadas']}")
        print(f"   ⭐ Favoritos processados: {self.stats['favoritos_processados']}")
        print(f"   ✅ Notificações enviadas: {self.stats['notificacoes_enviadas']}")
        print(f"   ❌ Notificações falharam: {self.stats['notificacoes_falharam']}")
        print("")
        
        if self.firebase_configurado and self.stats['notificacoes_enviadas'] > 0:
            print("🎉 NOTIFICAÇÕES ENVIADAS COM SUCESSO!")
            print(f"   📱 {self.stats['notificacoes_enviadas']} usuários notificados")
        elif not self.firebase_configurado:
            print("💡 PARA ATIVAR NOTIFICAÇÕES:")
            print("   1. Configure FIREBASE_PROJECT_ID nos secrets")
            print("   2. Configure FIREBASE_SERVICE_ACCOUNT nos secrets")  
            print("   3. Usuários se cadastram via web interface")
            print("   4. Dados salvos automaticamente no Firestore")
        else:
            print("ℹ️ NENHUMA NOTIFICAÇÃO ENVIADA")
            if self.stats['usuarios_ativos'] == 0:
                print("   Motivo: Nenhum usuário ativo encontrado")
            elif self.stats['mudancas_detectadas'] == 0:
                print("   Motivo: Nenhuma mudança detectada")
        
        print("")
        print("✅ Sistema principal não foi afetado")
        print("🌐 Web Interface: https://livel-analytics.web.app/")
        print("="*70)
    
    def executar(self):
        """Executa sistema completo - NUNCA falha o pipeline principal"""
        try:
            logger.info("🚀 Iniciando sistema de notificações Firebase + Firestore...")
            
            sucesso = self.processar_notificacoes()
            
            self.gerar_relatorio()
            
            # SEMPRE retorna sucesso para não quebrar pipeline
            return True
            
        except Exception as e:
            logger.error(f"Erro no sistema de notificações: {e}")
            logger.error(f"Trace: {traceback.format_exc()}")
            
            print(f"\n⚠️ Sistema de notificações com problemas: {e}")
            print("✅ Sistema principal não foi afetado")
            
            # SEMPRE retorna sucesso
            return True

def main():
    """Função principal"""
    try:
        notifier = LiveloFirebaseNotifier()
        notifier.executar()
        
        # SEMPRE sair com sucesso para não quebrar pipeline
        sys.exit(0)
        
    except Exception as e:
        print(f"⚠️ Erro nas notificações: {e}")
        print("✅ Sistema principal não foi afetado")
        
        # MESMO com erro, sair com sucesso
        sys.exit(0)

if __name__ == "__main__":
    main()
