#!/usr/bin/env python3
"""
Sistema de Notificações Firebase para Livelo Analytics - GitHub Actions
Caminhos corrigidos para ambiente GitHub Actions
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
        self.projeto_id = None
        self.script_dir = script_dir
        
        # Estatísticas
        self.stats = {
            'usuarios_ativos': 0,
            'notificacoes_enviadas': 0,
            'notificacoes_falharam': 0,
            'mudancas_detectadas': 0,
            'favoritos_processados': 0
        }
        
    def verificar_configuracao_firebase(self):
        """Verifica e configura Firebase Admin SDK v2"""
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
                from firebase_admin import credentials, messaging
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
                
                # Configurar messaging
                self.messaging = messaging
                self.firebase_configurado = True
                
                logger.info(f"Firebase configurado para: {self.projeto_id}")
                return True
                
            except Exception as e:
                logger.warning(f"Erro ao inicializar Firebase: {e}")
                return False
                
        except Exception as e:
            logger.warning(f"Erro na configuração Firebase: {e}")
            return False
    
    def carregar_usuarios_favoritos(self):
        """Carrega usuários e seus favoritos com caminhos corretos"""
        logger.info("Carregando usuários com favoritos...")
        
        # Arquivo de usuários com caminho absoluto
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
                "nome": "Usuário Demo 1"
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
                "nome": "Usuário Demo 2"
            }
        }
        
        # Tentar carregar do arquivo
        try:
            if os.path.exists(arquivo_usuarios):
                with open(arquivo_usuarios, 'r', encoding='utf-8') as f:
                    usuarios_data = json.load(f)
                    logger.info(f"Carregados {len(usuarios_data)} usuários do arquivo")
                    return usuarios_data
            else:
                logger.info(f"Arquivo não encontrado: {arquivo_usuarios}")
                logger.info("Usando dados de exemplo para demonstração")
                
                # Salvar exemplo para referência
                arquivo_exemplo = os.path.join(self.script_dir, 'usuarios_favoritos_exemplo.json')
                try:
                    with open(arquivo_exemplo, 'w', encoding='utf-8') as f:
                        json.dump(usuarios_exemplo, f, indent=2, ensure_ascii=False)
                    logger.info(f"Arquivo de exemplo criado: {arquivo_exemplo}")
                except Exception as e:
                    logger.warning(f"Erro ao criar arquivo de exemplo: {e}")
                
                return usuarios_exemplo
                
        except Exception as e:
            logger.warning(f"Erro ao carregar usuários: {e}")
            return usuarios_exemplo
    
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
                'url': 'https://gcaressato.github.io/livelo_scraper/',
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
                        icon='https://gcaressato.github.io/livelo_scraper/icon-192.png',
                        click_action='https://gcaressato.github.io/livelo_scraper/'
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
        
        # 2. Carregar usuários
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
            if not token:
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
                        logger.debug(f"Notificação enviada para {user_id}: {titulo}")
                    else:
                        logger.warning(f"Falha ao notificar {user_id}")
        
        return True
    
    def gerar_relatorio(self):
        """Gera relatório das notificações"""
        print("\n" + "="*60)
        print("🔔 SISTEMA DE NOTIFICAÇÕES FIREBASE")
        print("="*60)
        print(f"⏰ Executado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"📁 Diretório: {self.script_dir}")
        print(f"🔥 Firebase: {'✅ Configurado' if self.firebase_configurado else '❌ Não configurado'}")
        print("")
        print("📊 ESTATÍSTICAS:")
        print(f"   👥 Usuários ativos: {self.stats['usuarios_ativos']}")
        print(f"   📈 Mudanças detectadas: {self.stats['mudancas_detectadas']}")
        print(f"   ⭐ Favoritos processados: {self.stats['favoritos_processados']}")
        print(f"   ✅ Notificações enviadas: {self.stats['notificacoes_enviadas']}")
        print(f"   ❌ Notificações falharam: {self.stats['notificacoes_falharam']}")
        print("")
        
        if self.firebase_configurado and self.stats['notificacoes_enviadas'] > 0:
            print("🎉 NOTIFICAÇÕES ENVIADAS COM SUCESSO!")
        elif not self.firebase_configurado:
            print("💡 PARA ATIVAR NOTIFICAÇÕES:")
            print("   1. Configure FIREBASE_PROJECT_ID nos secrets")
            print("   2. Configure FIREBASE_SERVICE_ACCOUNT nos secrets")
            print("   3. Adicione usuários em usuarios_favoritos.json")
        else:
            print("ℹ️ NENHUMA NOTIFICAÇÃO ENVIADA")
        
        print("")
        print("✅ Sistema principal não foi afetado")
        print("="*60)
    
    def executar(self):
        """Executa sistema completo - NUNCA falha o pipeline principal"""
        try:
            logger.info("🚀 Iniciando sistema de notificações Firebase...")
            
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
    """Função principal - SEMPRE retorna sucesso"""
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
