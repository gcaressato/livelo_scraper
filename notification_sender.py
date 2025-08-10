#!/usr/bin/env python3
"""
Livelo Analytics - Sistema de Notificações Push
Envia notificações Firebase para usuários com favoritos em oferta
"""

import os
import sys
import json
import requests
import pandas as pd
from datetime import datetime, timedelta
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LiveloNotificationSender:
    def __init__(self):
        # Configurações do Firebase (via secrets do GitHub)
        self.project_id = os.getenv('FIREBASE_PROJECT_ID')
        self.server_key = os.getenv('FIREBASE_SERVER_KEY')
        self.fcm_url = f"https://fcm.googleapis.com/fcm/send"
        
        # Verificar se variáveis estão configuradas
        if not self.project_id or not self.server_key:
            logger.error("❌ FIREBASE_PROJECT_ID ou FIREBASE_SERVER_KEY não configurados")
            sys.exit(1)
            
        logger.info(f"✅ Firebase configurado para projeto: {self.project_id}")
        
        # Dados dos parceiros
        self.dados_hoje = None
        self.dados_ontem = None
        
    def carregar_dados(self):
        """Carrega dados do Excel"""
        try:
            if not os.path.exists('livelo_parceiros.xlsx'):
                logger.error("❌ Arquivo livelo_parceiros.xlsx não encontrado")
                return False
                
            df = pd.read_excel('livelo_parceiros.xlsx')
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            
            # Separar dados por data
            datas_unicas = sorted(df['Timestamp'].dt.date.unique(), reverse=True)
            
            if len(datas_unicas) >= 1:
                data_hoje = datas_unicas[0]
                self.dados_hoje = df[df['Timestamp'].dt.date == data_hoje].copy()
                logger.info(f"📊 Dados de hoje ({data_hoje}): {len(self.dados_hoje)} registros")
            
            if len(datas_unicas) >= 2:
                data_ontem = datas_unicas[1]
                self.dados_ontem = df[df['Timestamp'].dt.date == data_ontem].copy()
                logger.info(f"📊 Dados de ontem ({data_ontem}): {len(self.dados_ontem)} registros")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar dados: {e}")
            return False
    
    def detectar_mudancas_ofertas(self):
        """Detecta quais parceiros ganharam/perderam ofertas"""
        if self.dados_ontem is None:
            logger.warning("⚠️ Sem dados de ontem - não é possível detectar mudanças")
            return {'ganharam_oferta': [], 'perderam_oferta': []}
        
        mudancas = {'ganharam_oferta': [], 'perderam_oferta': []}
        
        # Preparar dados de hoje e ontem
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
                        'chave': chave
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
    
    def obter_tokens_usuarios(self):
        """Obtém tokens FCM dos usuários (simulado - na prática viria de um banco de dados)"""
        # Por enquanto, vamos usar um sistema baseado em arquivos
        # Na produção, isso seria um banco de dados
        
        tokens_file = 'user_fcm_tokens.json'
        if os.path.exists(tokens_file):
            try:
                with open(tokens_file, 'r') as f:
                    tokens_data = json.load(f)
                logger.info(f"📱 {len(tokens_data)} tokens de usuários encontrados")
                return tokens_data
            except Exception as e:
                logger.error(f"❌ Erro ao ler tokens: {e}")
        
        # Arquivo de exemplo (será criado na primeira execução)
        example_tokens = {
            "exemplo_user_1": {
                "fcm_token": "EXEMPLO_TOKEN_FCM_AQUI",
                "favoritos": ["Netshoes|R$", "Magazine Luiza|R$"],
                "ativo": True,
                "ultimo_acesso": datetime.now().isoformat()
            }
        }
        
        try:
            with open(tokens_file, 'w') as f:
                json.dump(example_tokens, f, indent=2)
            logger.info(f"📄 Arquivo exemplo criado: {tokens_file}")
        except Exception as e:
            logger.error(f"❌ Erro ao criar arquivo exemplo: {e}")
        
        return {}
    
    def enviar_notificacao_push(self, token, titulo, corpo, dados_extras=None):
        """Envia notificação push via Firebase FCM"""
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
                'badge': 'https://via.placeholder.com/96x96/ff0a8c/ffffff?text=L',
                'click_action': 'https://gc-livelo-analytics.github.io/',
                'tag': 'livelo-offer'
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
            response = requests.post(self.fcm_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success', 0) > 0:
                    logger.info(f"✅ Notificação enviada com sucesso")
                    return True
                else:
                    logger.error(f"❌ Falha no envio: {result}")
                    return False
            else:
                logger.error(f"❌ Erro HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro ao enviar notificação: {e}")
            return False
    
    def processar_notificacoes(self):
        """Processa e envia notificações para usuários relevantes"""
        # Detectar mudanças
        mudancas = self.detectar_mudancas_ofertas()
        
        # Obter tokens de usuários
        usuarios = self.obter_tokens_usuarios()
        
        if not usuarios:
            logger.warning("⚠️ Nenhum usuário registrado para notificações")
            return
        
        notificacoes_enviadas = 0
        
        for user_id, user_data in usuarios.items():
            if not user_data.get('ativo', False):
                continue
                
            token = user_data.get('fcm_token')
            favoritos = user_data.get('favoritos', [])
            
            if not token or not favoritos:
                continue
            
            # Verificar se algum favorito ganhou oferta
            favoritos_com_nova_oferta = []
            
            for oferta in mudancas['ganharam_oferta']:
                chave_oferta = oferta['chave']
                if chave_oferta in favoritos:
                    favoritos_com_nova_oferta.append(oferta)
            
            # Enviar notificação se houver ofertas relevantes
            if favoritos_com_nova_oferta:
                if len(favoritos_com_nova_oferta) == 1:
                    oferta = favoritos_com_nova_oferta[0]
                    titulo = f"🎯 {oferta['parceiro']} em oferta!"
                    pontos_por_moeda = oferta['pontos'] / oferta['valor'] if oferta['valor'] > 0 else 0
                    corpo = f"{pontos_por_moeda:.1f} pontos por {oferta['moeda']} - Aproveite agora!"
                    
                    dados_extras = {
                        'parceiro': oferta['parceiro'],
                        'moeda': oferta['moeda'],
                        'pontos': str(oferta['pontos']),
                        'valor': str(oferta['valor']),
                        'url': 'https://gc-livelo-analytics.github.io/'
                    }
                else:
                    titulo = f"🔥 {len(favoritos_com_nova_oferta)} favoritos em oferta!"
                    parceiros = [o['parceiro'] for o in favoritos_com_nova_oferta[:3]]
                    corpo = f"{', '.join(parceiros)}{'...' if len(favoritos_com_nova_oferta) > 3 else ''} - Confira no app!"
                    
                    dados_extras = {
                        'total_ofertas': str(len(favoritos_com_nova_oferta)),
                        'url': 'https://gc-livelo-analytics.github.io/'
                    }
                
                # Enviar notificação
                if self.enviar_notificacao_push(token, titulo, corpo, dados_extras):
                    notificacoes_enviadas += 1
                    logger.info(f"📱 Notificação enviada para {user_id}")
        
        logger.info(f"🚀 Total de notificações enviadas: {notificacoes_enviadas}")
        
        # Salvar estatísticas
        stats = {
            'timestamp': datetime.now().isoformat(),
            'novas_ofertas': len(mudancas['ganharam_oferta']),
            'ofertas_finalizadas': len(mudancas['perderam_oferta']),
            'usuarios_registrados': len(usuarios),
            'notificacoes_enviadas': notificacoes_enviadas
        }
        
        try:
            with open('notification_stats.json', 'w') as f:
                json.dump(stats, f, indent=2)
            logger.info("📊 Estatísticas salvas em notification_stats.json")
        except Exception as e:
            logger.error(f"❌ Erro ao salvar estatísticas: {e}")
    
    def executar(self):
        """Executa o processo completo de notificações"""
        logger.info("🚀 Iniciando sistema de notificações Livelo Analytics")
        
        # Carregar dados
        if not self.carregar_dados():
            logger.error("❌ Falha ao carregar dados - abortando")
            return False
        
        # Processar e enviar notificações
        self.processar_notificacoes()
        
        logger.info("✅ Processo de notificações concluído")
        return True

def main():
    """Função principal"""
    sender = LiveloNotificationSender()
    sucesso = sender.executar()
    
    if not sucesso:
        sys.exit(1)

if __name__ == "__main__":
    main()
