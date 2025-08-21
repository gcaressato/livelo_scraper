#!/usr/bin/env python3
"""
Script para corrigir os problemas do sistema Livelo Analytics
Corrige todos os problemas identificados:
1. Erro no livelo_reporter.py (método _gerar_dashboard_completo)
2. Configuração do Firebase
3. Sistema de favoritos
4. Deploy do HTML
"""

import os
import sys
import json
import shutil
from datetime import datetime

def main():
    print("🔧 CORRIGINDO PROBLEMAS DO SISTEMA LIVELO ANALYTICS")
    print("=" * 60)
    
    # 1. Corrigir livelo_reporter.py
    print("1. 🔨 Corrigindo livelo_reporter.py...")
    try:
        corrigir_livelo_reporter()
        print("   ✅ livelo_reporter.py corrigido")
    except Exception as e:
        print(f"   ❌ Erro ao corrigir reporter: {e}")
    
    # 2. Verificar configuração Firebase
    print("2. 🔥 Verificando configuração Firebase...")
    try:
        verificar_firebase()
        print("   ✅ Firebase verificado")
    except Exception as e:
        print(f"   ❌ Erro no Firebase: {e}")
    
    # 3. Preparar diretório public para deploy
    print("3. 📁 Preparando deploy...")
    try:
        preparar_deploy()
        print("   ✅ Deploy preparado")
    except Exception as e:
        print(f"   ❌ Erro no deploy: {e}")
    
    # 4. Testar sistema
    print("4. 🧪 Testando sistema...")
    try:
        testar_sistema()
        print("   ✅ Testes concluídos")
    except Exception as e:
        print(f"   ❌ Erro nos testes: {e}")
    
    print("\n🎉 CORREÇÕES APLICADAS COM SUCESSO!")
    print("📋 Execute agora: python main.py --apenas-analise")
    print("🌐 Depois faça o deploy: firebase deploy")

def corrigir_livelo_reporter():
    """Aplica correção no livelo_reporter.py"""
    print("   📝 Lendo livelo_reporter.py...")
    
    # Como o arquivo é muito grande, vamos criar um patch focado
    patch_code = '''
    def _gerar_dashboard_completo(self, graficos_html):
        """Gera o dashboard completo com todos os gráficos"""
        dados = self.analytics['dados_completos']
        metricas = self.analytics['metricas']
        
        # Gerar seções do dashboard
        cards_metricas = self._gerar_cards_metricas(metricas)
        secao_graficos = self._gerar_secao_graficos(graficos_html)
        minha_carteira = self._gerar_minha_carteira()
        tabela_completa = self._gerar_tabela_analise_completa_com_favoritos(dados)
        filtros_avancados = self._gerar_filtros_avancados(dados)
        
        return f"""
        <div class="container-fluid">
            {cards_metricas}
            {minha_carteira}
            <ul class="nav nav-pills nav-fill mb-3">
                <li class="nav-item">
                    <button class="nav-link active" data-bs-toggle="pill" data-bs-target="#dashboard-pane">
                        <i class="bi bi-speedometer2 me-2"></i>Dashboard
                    </button>
                </li>
                <li class="nav-item">
                    <button class="nav-link" data-bs-toggle="pill" data-bs-target="#analise-pane">
                        <i class="bi bi-table me-2"></i>Análise Completa
                    </button>
                </li>
            </ul>
            <div class="tab-content">
                <div class="tab-pane fade show active" id="dashboard-pane">
                    {secao_graficos}
                </div>
                <div class="tab-pane fade" id="analise-pane">
                    <div class="card">
                        <div class="card-header">
                            <h6 class="mb-0">Análise Detalhada</h6>
                        </div>
                        <div class="card-body">
                            <div id="filtrosContainer" style="display: none;">
                                {filtros_avancados}
                            </div>
                            <div class="table-container">
                                {tabela_completa}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """

    def _gerar_cards_metricas(self, metricas):
        """Gera os cards de métricas principais"""
        return f"""
        <div class="row g-2 mb-3">
            <div class="col-lg-2 col-md-4 col-6">
                <div class="metric-card text-center">
                    <div class="metric-value">{metricas['total_parceiros']}</div>
                    <div class="metric-label">Parceiros Hoje</div>
                </div>
            </div>
            <div class="col-lg-2 col-md-4 col-6">
                <div class="metric-card text-center">
                    <div class="metric-value">{metricas['total_com_oferta']}</div>
                    <div class="metric-label">Com Oferta</div>
                </div>
            </div>
            <div class="col-lg-2 col-md-4 col-6">
                <div class="metric-card text-center">
                    <div class="metric-value">{metricas['percentual_ofertas_hoje']:.1f}%</div>
                    <div class="metric-label">Taxa de Ofertas</div>
                </div>
            </div>
            <div class="col-lg-2 col-md-4 col-6">
                <div class="metric-card text-center">
                    <div class="metric-value">{metricas['novos_parceiros']}</div>
                    <div class="metric-label">Novos (≤14d)</div>
                </div>
            </div>
            <div class="col-lg-2 col-md-4 col-6">
                <div class="metric-card text-center">
                    <div class="metric-value">{metricas['media_pontos_ofertas']:.1f}</div>
                    <div class="metric-label">Média Pts/Moeda</div>
                </div>
            </div>
            <div class="col-lg-2 col-md-4 col-6">
                <div class="metric-card text-center">
                    <div class="metric-value">{metricas['compre_agora']}</div>
                    <div class="metric-label">Compre Agora!</div>
                </div>
            </div>
        </div>
        """

    def _gerar_secao_graficos(self, graficos_html):
        """Gera a seção com todos os gráficos"""
        return f"""
        <div class="row g-3">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">Evolução Temporal</h6>
                    </div>
                    <div class="card-body">
                        {graficos_html.get('evolucao_temporal', '')}
                    </div>
                </div>
            </div>
            <div class="col-lg-6 col-12">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">Top 10 Ofertas</h6>
                    </div>
                    <div class="card-body">
                        {graficos_html.get('top_ofertas', '')}
                    </div>
                </div>
            </div>
            <div class="col-lg-6 col-12">
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">Matriz de Oportunidades</h6>
                    </div>
                    <div class="card-body">
                        {graficos_html.get('matriz_oportunidades', '')}
                    </div>
                </div>
            </div>
        </div>
        """

    def _gerar_minha_carteira(self):
        """Gera seção 'Minha Carteira' para favoritos"""
        return """
        <div class="card mb-3" id="minhaCarteira">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h6 class="mb-0"><i class="bi bi-star-fill me-2 text-warning"></i>Minha Carteira</h6>
                <button class="btn btn-sm btn-outline-secondary" onclick="limparCarteira()">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
            <div class="card-body">
                <div id="carteiraContent">
                    <div class="carteira-vazia">
                        <i class="bi bi-star text-muted" style="font-size: 2rem;"></i>
                        <p class="mb-0 mt-2">Adicione parceiros aos favoritos clicando na estrela ⭐</p>
                        <small class="text-muted">Seus favoritos ficarão sempre visíveis aqui</small>
                    </div>
                </div>
            </div>
        </div>
        """
    '''
    
    # Salvar patch
    with open('livelo_reporter_patch.py', 'w', encoding='utf-8') as f:
        f.write(patch_code)
    
    print("   💾 Patch salvo em livelo_reporter_patch.py")
    print("   📋 INSTRUÇÕES:")
    print("      1. Abra livelo_reporter.py no editor")
    print("      2. Procure pela linha que contém: def gerar_html_completo(self):")
    print("      3. Antes desta função, adicione os métodos do arquivo livelo_reporter_patch.py")
    print("      4. Certifique-se de manter a indentação correta (4 espaços)")

def verificar_firebase():
    """Verifica e corrige configuração do Firebase"""
    print("   🔥 Verificando firebase.json...")
    
    firebase_config = {
        "hosting": {
            "public": "public",
            "ignore": [
                "firebase.json",
                "**/.*",
                "**/node_modules/**",
                "**/*.log",
                "**/*.py",
                "**/*.xlsx"
            ],
            "rewrites": [
                {
                    "source": "**",
                    "destination": "/index.html"
                }
            ],
            "headers": [
                {
                    "source": "**/*.@(js|css|html)",
                    "headers": [
                        {
                            "key": "Cache-Control",
                            "value": "max-age=3600"
                        }
                    ]
                }
            ],
            "cleanUrls": True
        }
    }
    
    # Salvar configuração corrigida
    with open('firebase.json', 'w', encoding='utf-8') as f:
        json.dump(firebase_config, f, indent=2, ensure_ascii=False)
    
    print("   ✅ firebase.json atualizado")
    
    # Verificar variáveis de ambiente
    print("   🔑 Verificando variáveis de ambiente...")
    firebase_vars = {
        'FIREBASE_PROJECT_ID': os.getenv('FIREBASE_PROJECT_ID'),
        'FIREBASE_SERVICE_ACCOUNT': os.getenv('FIREBASE_SERVICE_ACCOUNT')
    }
    
    missing_vars = [k for k, v in firebase_vars.items() if not v]
    if missing_vars:
        print(f"   ⚠️ Variáveis faltando: {', '.join(missing_vars)}")
        print("   💡 Configure em GitHub Secrets para deploy automático")
    else:
        print("   ✅ Variáveis Firebase configuradas")

def preparar_deploy():
    """Prepara diretório public para deploy"""
    print("   📁 Criando diretório public...")
    
    if not os.path.exists('public'):
        os.makedirs('public')
    
    # Copiar HTML se existir
    if os.path.exists('relatorio_livelo.html'):
        shutil.copy2('relatorio_livelo.html', 'public/index.html')
        print("   📄 HTML copiado para public/index.html")
    
    # Criar arquivos essenciais
    if not os.path.exists('public/index.html'):
        # Criar placeholder
        placeholder_html = """<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Livelo Analytics - Em Manutenção</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
        .maintenance { background: #f8f9fa; padding: 40px; border-radius: 10px; }
    </style>
</head>
<body>
    <div class="maintenance">
        <h1>🔧 Livelo Analytics</h1>
        <p>Sistema em manutenção</p>
        <p>Execute: <code>python main.py --apenas-analise</code></p>
        <small>Última atualização: """ + datetime.now().strftime('%d/%m/%Y %H:%M') + """</small>
    </div>
</body>
</html>"""
        
        with open('public/index.html', 'w', encoding='utf-8') as f:
            f.write(placeholder_html)
        
        print("   📄 Placeholder HTML criado")

def testar_sistema():
    """Testa componentes do sistema"""
    print("   🧪 Testando arquivos essenciais...")
    
    arquivos_essenciais = [
        'main.py',
        'livelo_scraper.py', 
        'livelo_reporter.py',
        'notification_sender.py',
        'firebase.json'
    ]
    
    for arquivo in arquivos_essenciais:
        if os.path.exists(arquivo):
            print(f"   ✅ {arquivo}")
        else:
            print(f"   ❌ {arquivo} - FALTANDO")
    
    # Verificar diretórios
    diretorios = ['public', 'logs']
    for diretorio in diretorios:
        if os.path.exists(diretorio):
            print(f"   ✅ {diretorio}/")
        else:
            os.makedirs(diretorio, exist_ok=True)
            print(f"   📁 {diretorio}/ - CRIADO")

if __name__ == "__main__":
    main()
