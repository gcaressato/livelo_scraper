    def gerar_html_completo(self):
        """Gera HTML completo com todas as funcionalidades atualizadas + NOTIFICAÇÕES FIREBASE"""
        dados = self.analytics['dados_completos']
        metricas = self.analytics['metricas']
        graficos = self.analytics['graficos']
        mudancas = self.analytics['mudancas_ofertas']
        
        # Converter gráficos para HTML
        graficos_html = {}
        for key, fig in graficos.items():
            graficos_html[key] = fig.to_html(full_html=False, include_plotlyjs='cdn')
        
        # Preparar dados para JavaScript
        dados_json = dados.to_json(orient='records', date_format='iso')
        dados_historicos_completos = self.df_completo.copy()
        dados_historicos_completos['Timestamp'] = dados_historicos_completos['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        dados_historicos_json = dados_historicos_completos.to_json(orient='records')
        dados_raw_json = self.df_completo.to_json(orient='records', date_format='iso')
        
        # Preparar alertas dinâmicos + NOVOS ALERTAS INTELIGENTES
        alertas_html = self._gerar_alertas_dinamicos_inteligentes(mudancas, metricas, dados)
        
        # Gerar filtros avançados
        filtros_html = self._gerar_filtros_avancados(dados)
        
        html = f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Livelo Analytics Pro - {metricas['ultima_atualizacao']}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>

        <!-- PWA Manifest -->
        <link rel="manifest" href="manifest.json">
        <meta name="theme-color" content="#ff0a8c">

        <!-- Firebase SDK v9 - NOTIFICAÇÕES -->
        <script type="module">
            import {{ initializeApp }} from 'https://www.gstatic.com/firebasejs/9.23.0/firebase-app.js';
            import {{ getMessaging, getToken, onMessage }} from 'https://www.gstatic.com/firebasejs/9.23.0/firebase-messaging.js';
            
            // Configuração Firebase (será preenchida dinamicamente)
            const firebaseConfig = {{
                apiKey: "API_KEY_PLACEHOLDER",
                authDomain: "PROJECT_ID.firebaseapp.com",
                projectId: "PROJECT_ID",
                storageBucket: "PROJECT_ID.appspot.com",
                messagingSenderId: "SENDER_ID",
                appId: "APP_ID"
            }};
            
            // Tentar obter config do servidor (para produção)
            try {{
                const configResponse = await fetch('/firebase-config.json');
                if (configResponse.ok) {{
                    const serverConfig = await configResponse.json();
                    Object.assign(firebaseConfig, serverConfig);
                }}
            }} catch (e) {{
                console.log('Config local será usada');
            }}
            
            const app = initializeApp(firebaseConfig);
            const messaging = getMessaging(app);
            
            window.firebaseMessaging = messaging;
        </script>
        
        <style>
            :root {{
                --livelo-rosa: {LIVELO_ROSA};
                --livelo-azul: {LIVELO_AZUL};
                --livelo-rosa-claro: {LIVELO_ROSA_CLARO};
                --livelo-azul-claro: {LIVELO_AZUL_CLARO};
            }}
            
            /* TEMA CLARO (padrão) */
            :root {{
                --bg-primary: #f8f9fa;
                --bg-secondary: #e9ecef;
                --bg-card: white;
                --text-primary: #212529;
                --text-secondary: #6c757d;
                --border-color: #dee2e6;
                --shadow: rgba(0,0,0,0.06);
                --shadow-hover: rgba(0,0,0,0.1);
            }}
            
            /* TEMA ESCURO - CONTRASTE MELHORADO E CORRIGIDO */
            [data-theme="dark"] {{
                --bg-primary: #1a1d23;
                --bg-secondary: #2d3139;
                --bg-card: #3a3f4b;
                --text-primary: #ffffff;
                --text-secondary: #d1d5db;
                --border-color: #6b7280;
                --shadow: rgba(0,0,0,0.4);
                --shadow-hover: rgba(0,0,0,0.6);
            }}
            
            /* ESTILOS PARA NOTIFICAÇÕES */
            .notification-toggle {{
                position: fixed;
                top: 80px;
                right: 20px;
                z-index: 999;
                background: var(--bg-card);
                border: 2px solid var(--border-color);
                border-radius: 25px;
                width: 50px;
                height: 50px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 2px 10px var(--shadow);
            }}
            
            .notification-toggle:hover {{
                transform: scale(1.1);
                box-shadow: 0 4px 15px var(--shadow-hover);
                border-color: var(--livelo-rosa);
            }}
            
            .notification-toggle.active {{
                background: var(--livelo-rosa);
                border-color: var(--livelo-rosa);
            }}
            
            .notification-toggle.active i {{
                color: white !important;
            }}
            
            .notification-status {{
                position: fixed;
                top: 140px;
                right: 20px;
                z-index: 998;
                background: var(--bg-card);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 0.8rem;
                color: var(--text-secondary);
                box-shadow: 0 2px 8px var(--shadow);
                transform: translateX(150%);
                transition: all 0.3s ease;
            }}
            
            .notification-status.show {{
                transform: translateX(0);
            }}
            
            .notification-banner {{
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                background: linear-gradient(135deg, var(--livelo-rosa) 0%, var(--livelo-azul) 100%);
                color: white;
                padding: 10px;
                text-align: center;
                z-index: 1001;
                transform: translateY(-100%);
                transition: all 0.3s ease;
                font-size: 0.9rem;
            }}
            
            .notification-banner.show {{
                transform: translateY(0);
            }}
            
            .notification-banner button {{
                background: rgba(255,255,255,0.2);
                border: 1px solid rgba(255,255,255,0.3);
                color: white;
                padding: 4px 12px;
                border-radius: 15px;
                margin-left: 10px;
                font-size: 0.8rem;
            }}
            
            .notification-banner button:hover {{
                background: rgba(255,255,255,0.3);
            }}
            
            [data-theme="dark"] .notification-toggle {{
                background: var(--bg-card);
                border-color: var(--livelo-rosa);
            }}
            
            [data-theme="dark"] .notification-toggle:hover {{
                background: var(--livelo-rosa);
            }}
            
            [data-theme="dark"] .notification-toggle:hover i {{
                color: white;
            }}
            
            /* Resto dos estilos CSS permanecem iguais... */
            
            /* [TODOS OS OUTROS ESTILOS CSS EXISTENTES PERMANECEM IGUAIS] */
            
            [data-theme="dark"] body {{
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                color: #ffffff;
            }}
            
            [data-theme="dark"] .table th {{
                background-color: #1e40af !important;
                color: #ffffff !important;
                border-color: #374151 !important;
            }}
            
            [data-theme="dark"] .table td {{
                background-color: #374151 !important;
                color: #f9fafb !important;
                border-color: #4b5563 !important;
            }}
            
            [data-theme="dark"] .table tbody tr:hover {{
                background-color: rgba(255, 10, 140, 0.2) !important;
            }}
            
            [data-theme="dark"] .form-select {{
                background-color: #374151 !important;
                color: #f9fafb !important;
                border-color: #6b7280 !important;
            }}
            
            [data-theme="dark"] .form-select:focus {{
                background-color: #374151 !important;
                color: #f9fafb !important;
                border-color: var(--livelo-rosa) !important;
                box-shadow: 0 0 0 0.2rem rgba(255, 10, 140, 0.25) !important;
            }}
            
            [data-theme="dark"] .form-select option {{
                background-color: #374151 !important;
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] .form-label {{
                color: #f9fafb !important;
                font-weight: 600 !important;
            }}
            
            [data-theme="dark"] .alert-details {{
                background: rgba(55, 65, 81, 0.5) !important;
                border-color: #6b7280 !important;
            }}
            
            [data-theme="dark"] .alert-compact {{
                background: #374151 !important;
                border-color: #6b7280 !important;
            }}
            
            [data-theme="dark"] .alert-header:hover {{
                background: rgba(255, 10, 140, 0.1) !important;
            }}
            
            [data-theme="dark"] .alert-title {{
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] .alert-preview {{
                color: #d1d5db !important;
            }}
            
            [data-theme="dark"] .alert-content h6 {{
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] .alert-content small {{
                color: #d1d5db !important;
            }}
            
            [data-theme="dark"] .alert-stats {{
                color: #d1d5db !important;
            }}
            
            [data-theme="dark"] .card {{
                background: #374151 !important;
                border-color: #6b7280 !important;
            }}
            
            [data-theme="dark"] .card-header {{
                background: #4b5563 !important;
                border-color: #6b7280 !important;
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] .card-header h6 {{
                color: #f9fafb !important;
                font-weight: 600 !important;
            }}
            
            [data-theme="dark"] .metric-card {{
                background: linear-gradient(135deg, #374151 0%, #4b5563 100%) !important;
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] .metric-value {{
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] .metric-label {{
                color: #d1d5db !important;
            }}
            
            [data-theme="dark"] .search-input {{
                background-color: #374151 !important;
                color: #f9fafb !important;
                border-color: #6b7280 !important;
            }}
            
            [data-theme="dark"] .search-input:focus {{
                background-color: #374151 !important;
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] .search-input::placeholder {{
                color: #9ca3af !important;
            }}
            
            /* CORREÇÕES ADICIONAIS PARA CONTRASTE */
            [data-theme="dark"] h1 {{
                color: #f9fafb !important;
                text-shadow: 0 2px 4px rgba(0,0,0,0.3);
            }}
            
            [data-theme="dark"] .text-muted {{
                color: #d1d5db !important;
            }}
            
            [data-theme="dark"] .text-secondary {{
                color: #d1d5db !important;
            }}
            
            [data-theme="dark"] .fw-bold:not(.badge):not(.btn) {{
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] strong {{
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] h6 {{
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] label {{
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] small {{
                color: #d1d5db !important;
            }}
            
            /* ANÁLISE INDIVIDUAL - RESUMO ESTATÍSTICO */
            [data-theme="dark"] .individual-analysis {{
                background-color: #374151 !important;
                border: 1px solid #6b7280 !important;
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] .individual-analysis .form-label {{
                color: #f9fafb !important;
                font-weight: 600 !important;
            }}
            
            [data-theme="dark"] .individual-analysis .fw-bold {{
                color: #ffffff !important;
            }}
            
            [data-theme="dark"] .individual-analysis .card {{
                background-color: #4b5563 !important;
                border-color: #6b7280 !important;
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] .individual-analysis .card .fw-bold {{
                color: #ffffff !important;
            }}
            
            [data-theme="dark"] .individual-analysis .card .text-primary {{
                color: #60a5fa !important;
            }}
            
            [data-theme="dark"] .individual-analysis .card .text-info {{
                color: #22d3ee !important;
            }}
            
            [data-theme="dark"] .individual-analysis .card .text-success {{
                color: #4ade80 !important;
            }}
            
            [data-theme="dark"] .individual-analysis .card .text-warning {{
                color: #fbbf24 !important;
            }}
            
            [data-theme="dark"] .individual-analysis .card .text-secondary {{
                color: #d1d5db !important;
            }}
            
            [data-theme="dark"] .individual-analysis .card .text-dark {{
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] .individual-analysis .card .text-muted {{
                color: #9ca3af !important;
            }}
            
            [data-theme="dark"] .individual-analysis .bg-light {{
                background-color: #374151 !important;
                border-color: #6b7280 !important;
            }}
            
            [data-theme="dark"] .individual-analysis .bg-white {{
                background-color: #4b5563 !important;
            }}
            
            [data-theme="dark"] .individual-analysis .btn-outline-primary {{
                color: #60a5fa !important;
                border-color: #60a5fa !important;
                background-color: transparent !important;
            }}
            
            [data-theme="dark"] .individual-analysis .btn-outline-primary:hover {{
                color: #ffffff !important;
                background-color: #60a5fa !important;
                border-color: #60a5fa !important;
            }}
            
            /* ABAS E NAVEGAÇÃO */
            [data-theme="dark"] .nav-pills .nav-link {{
                color: #d1d5db !important;
                background-color: #4b5563;
                border: 1px solid #6b7280;
            }}
            
            [data-theme="dark"] .nav-pills .nav-link:hover {{
                background-color: #6b7280 !important;
                color: #ffffff !important;
            }}
            
            [data-theme="dark"] .nav-pills .nav-link.active {{
                background-color: var(--livelo-rosa) !important;
                color: #ffffff !important;
                border-color: var(--livelo-rosa) !important;
            }}
            
            /* RODAPÉ */
            [data-theme="dark"] .footer {{
                color: #d1d5db !important;
                border-top-color: #6b7280 !important;
            }}
            
            [data-theme="dark"] .footer small:hover {{
                color: #60a5fa !important;
            }}
            
            /* CONTROLES TEMPORAIS - CSS ESPECÍFICO */
            .filtros-temporais-container {{
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
            }}
            
            .filtros-label {{
                color: #495057;
            }}
            
            .filtro-temporal-select {{
                background-color: white;
                color: #495057;
                border-color: #ced4da;
            }}
            
            .filtro-temporal-btn {{
                color: #6c757d;
                border-color: #6c757d;
            }}
            
            .filtro-status {{
                color: #6c757d;
            }}
            
            [data-theme="dark"] .filtros-temporais-container {{
                background-color: #374151 !important;
                border-color: #6b7280 !important;
            }}
            
            [data-theme="dark"] .filtros-label {{
                color: #f9fafb !important;
                font-weight: 600;
            }}
            
            [data-theme="dark"] .filtro-temporal-select {{
                background-color: #4b5563 !important;
                color: #f9fafb !important;
                border-color: #6b7280 !important;
            }}
            
            [data-theme="dark"] .filtro-temporal-select:focus {{
                background-color: #4b5563 !important;
                color: #f9fafb !important;
                border-color: var(--livelo-rosa) !important;
                box-shadow: 0 0 0 0.2rem rgba(255, 10, 140, 0.25) !important;
            }}
            
            [data-theme="dark"] .filtro-temporal-select option {{
                background-color: #4b5563 !important;
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] .filtro-temporal-btn {{
                color: #d1d5db !important;
                border-color: #6b7280 !important;
                background-color: #4b5563 !important;
            }}
            
            [data-theme="dark"] .filtro-temporal-btn:hover {{
                color: #ffffff !important;
                border-color: var(--livelo-rosa) !important;
                background-color: var(--livelo-rosa) !important;
            }}
            
            [data-theme="dark"] .filtro-status {{
                color: #d1d5db !important;
            }}
            
            [data-theme="dark"] .filtro-status.text-primary {{
                color: #60a5fa !important;
            }}
            
            [data-theme="dark"] .filtro-status.text-muted {{
                color: #9ca3af !important;
            }}
            
            /* ========== RESUMO ESTATÍSTICO - CONTRASTE CORRIGIDO ========== */
            .resumo-estatistico-container {{
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 12px;
                margin-top: 20px;
            }}
            
            .resumo-titulo {{
                color: #495057 !important;
                font-weight: 600 !important;
                margin-bottom: 15px !important;
            }}
            
            /* MODO ESCURO - RESUMO ESTATÍSTICO */
            [data-theme="dark"] .resumo-estatistico-container {{
                background-color: #374151 !important;
                border-color: #6b7280 !important;
            }}
            
            [data-theme="dark"] .resumo-titulo {{
                color: #f9fafb !important;
                font-weight: 600 !important;
            }}
            
            [data-theme="dark"] .resumo-estatistico-container .card {{
                background-color: #4b5563 !important;
                border-color: #6b7280 !important;
            }}
            
            [data-theme="dark"] .resumo-estatistico-container .fw-bold {{
                color: #ffffff !important;
            }}
            
            [data-theme="dark"] .resumo-estatistico-container .text-primary {{
                color: #60a5fa !important;
            }}
            
            [data-theme="dark"] .resumo-estatistico-container .text-info {{
                color: #22d3ee !important;
            }}
            
            [data-theme="dark"] .resumo-estatistico-container .text-success {{
                color: #4ade80 !important;
            }}
            
            [data-theme="dark"] .resumo-estatistico-container .text-warning {{
                color: #fbbf24 !important;
            }}
            
            [data-theme="dark"] .resumo-estatistico-container .text-secondary {{
                color: #d1d5db !important;
            }}
            
            [data-theme="dark"] .resumo-estatistico-container .text-dark {{
                color: #f9fafb !important;
            }}
            
            [data-theme="dark"] .resumo-estatistico-container .text-muted {{
                color: #9ca3af !important;
            }}
            
            [data-theme="dark"] .resumo-estatistico-container .btn-outline-primary {{
                color: #60a5fa !important;
                border-color: #60a5fa !important;
            }}
            
            [data-theme="dark"] .resumo-estatistico-container .btn-outline-primary:hover {{
                color: #ffffff !important;
                background-color: #60a5fa !important;
                border-color: #60a5fa !important;
            }}
            
            /* ========== MINHA CARTEIRA - ESTILOS ========== */
            .favorito-btn {{
                background: none;
                border: none;
                cursor: pointer;
                padding: 2px 5px;
                border-radius: 50%;
                transition: all 0.2s ease;
            }}
            
            .favorito-btn:hover {{
                background: rgba(255, 10, 140, 0.1);
                transform: scale(1.1);
            }}
            
            .favorito-btn.ativo {{
                color: #ffc107;
            }}
            
            .favorito-btn:not(.ativo) {{
                color: #ccc;
            }}
            
            .carteira-vazia {{
                text-align: center;
                padding: 40px 20px;
                color: var(--text-secondary);
            }}
            
            .carteira-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px 15px;
                background: var(--bg-card);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                margin-bottom: 10px;
                transition: all 0.2s ease;
            }}
            
            .carteira-item:hover {{
                background: rgba(255, 10, 140, 0.05);
                border-color: var(--livelo-rosa);
            }}
            
            .carteira-nome {{
                font-weight: 500;
                color: var(--text-primary);
            }}
            
            .carteira-info {{
                font-size: 0.85rem;
                color: var(--text-secondary);
            }}
            
            .carteira-pontos {{
                font-weight: 600;
                color: var(--livelo-rosa);
            }}
            
            [data-theme="dark"] .carteira-item {{
                background: #4b5563;
                border-color: #6b7280;
            }}
            
            [data-theme="dark"] .carteira-item:hover {{
                background: rgba(255, 10, 140, 0.1);
            }}
            
            * {{ box-sizing: border-box; }}
            
            body {{
                background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 14px;
                line-height: 1.4;
                color: var(--text-primary);
                transition: all 0.3s ease;
            }}
            
            .container-fluid {{ 
                max-width: 100%; 
                padding: 10px 15px; 
            }}
            
            /* THEME TOGGLE - MELHORADO */
            .theme-toggle {{
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1000;
                background: var(--bg-card);
                border: 2px solid var(--border-color);
                border-radius: 25px;
                width: 50px;
                height: 50px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 2px 10px var(--shadow);
            }}
            
            .theme-toggle:hover {{
                transform: scale(1.1);
                box-shadow: 0 4px 15px var(--shadow-hover);
                border-color: var(--livelo-rosa);
            }}
            
            .theme-toggle i {{
                font-size: 1.2rem;
                color: var(--text-primary);
                transition: all 0.3s ease;
            }}
            
            [data-theme="dark"] .theme-toggle {{
                background: var(--bg-card);
                border-color: var(--livelo-rosa);
            }}
            
            [data-theme="dark"] .theme-toggle:hover {{
                background: var(--livelo-rosa);
            }}
            
            [data-theme="dark"] .theme-toggle:hover i {{
                color: white;
            }}
            
            /* ALERTAS COMPACTOS */
            .alerts-container {{
                margin-bottom: 20px;
            }}
            
            .alert-compact {{
                background: var(--bg-card);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                margin-bottom: 10px;
                overflow: hidden;
                transition: all 0.3s ease;
                box-shadow: 0 2px 8px var(--shadow);
            }}
            
            .alert-compact:hover {{
                box-shadow: 0 4px 15px var(--shadow-hover);
                transform: translateY(-1px);
            }}
            
            .alert-header {{
                padding: 12px 15px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                cursor: pointer;
                user-select: none;
                transition: all 0.2s ease;
            }}
            
            .alert-header:hover {{
                background: rgba(255, 10, 140, 0.05);
            }}
            
            .alert-title {{
                display: flex;
                align-items: center;
                flex: 1;
                color: var(--text-primary);
            }}
            
            .alert-title strong {{
                margin-right: 10px;
            }}
            
            .alert-chevron {{
                margin-left: auto;
                margin-right: 10px;
                transition: transform 0.3s ease;
                color: var(--text-secondary);
            }}
            
            .alert-compact.expanded .alert-chevron {{
                transform: rotate(180deg);
            }}
            
            .alert-close {{
                background: none;
                border: none;
                font-size: 1.2rem;
                color: var(--text-secondary);
                cursor: pointer;
                padding: 0;
                width: 24px;
                height: 24px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                transition: all 0.2s ease;
            }}
            
            .alert-close:hover {{
                background: rgba(220, 53, 69, 0.1);
                color: #dc3545;
            }}
            
            .alert-preview {{
                padding: 0 15px 12px 15px;
                color: var(--text-secondary);
            }}
            
            .alert-details {{
                border-top: 1px solid var(--border-color);
                background: rgba(0,0,0,0.02);
                animation: slideDown 0.3s ease;
            }}
            
            .alert-content {{
                padding: 15px;
            }}
            
            .alert-content h6 {{
                margin-bottom: 10px;
                color: var(--text-primary);
                font-size: 0.9rem;
            }}
            
            /* GRIDS E LISTAS DOS ALERTAS */
            .partners-grid {{
                display: flex;
                flex-wrap: wrap;
                gap: 5px;
                margin-bottom: 10px;
            }}
            
            .partner-tag, .lost-tag {{
                background: var(--livelo-rosa);
                color: white;
                padding: 3px 8px;
                border-radius: 12px;
                font-size: 0.7rem;
                font-weight: 500;
            }}
            
            .lost-tag {{
                background: #dc3545;
            }}
            
            .ranking-list, .rare-opportunities, .increases-list, .newbies-list, .lost-offers {{
                display: flex;
                flex-direction: column;
                gap: 5px;
            }}
            
            .lost-offers {{
                display: flex;
                flex-direction: row;
                flex-wrap: wrap;
                gap: 5px;
            }}
            
            .rank-item, .rare-item, .increase-item, .newbie-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 5px 10px;
                background: var(--bg-primary);
                border-radius: 6px;
                font-size: 0.8rem;
            }}
            
            .rank-number {{
                background: var(--livelo-rosa);
                color: white;
                padding: 2px 6px;
                border-radius: 10px;
                font-weight: bold;
                font-size: 0.7rem;
                min-width: 25px;
                text-align: center;
            }}
            
            .rank-points, .rare-points {{
                background: var(--livelo-azul);
                color: white;
                padding: 2px 8px;
                border-radius: 8px;
                font-weight: 500;
                font-size: 0.7rem;
            }}
            
            .rare-freq {{
                background: #ffc107;
                color: #212529;
                padding: 2px 6px;
                border-radius: 6px;
                font-size: 0.7rem;
                font-weight: 500;
            }}
            
            .increase-percent {{
                font-weight: bold;
                font-size: 0.8rem;
            }}
            
            /* CORES DOS ALERTAS */
            .alert-success {{ border-left: 4px solid #28a745; }}
            .alert-danger {{ border-left: 4px solid #dc3545; }}
            .alert-warning {{ border-left: 4px solid #ffc107; }}
            .alert-info {{ border-left: 4px solid #17a2b8; }}
            .alert-default {{ border-left: 4px solid var(--livelo-rosa); }}
            .alert-intelligent {{ border-left: 4px solid #9c27b0; }}
            
            /* ANIMAÇÃO */
            @keyframes slideDown {{
                from {{
                    opacity: 0;
                    max-height: 0;
                }}
                to {{
                    opacity: 1;
                    max-height: 500px;
                }}
            }}
            
            .card {{
                border: none;
                border-radius: 12px;
                box-shadow: 0 2px 12px var(--shadow);
                transition: all 0.3s ease;
                margin-bottom: 15px;
                background: var(--bg-card);
                color: var(--text-primary);
            }}
            
            .card:hover {{ 
                transform: translateY(-1px); 
                box-shadow: 0 4px 20px var(--shadow-hover); 
            }}
            
            .metric-card {{
                background: linear-gradient(135deg, var(--bg-card) 0%, var(--bg-primary) 100%);
                border-left: 3px solid var(--livelo-rosa);
                padding: 15px;
            }}
            
            .metric-value {{
                font-size: 1.8rem;
                font-weight: 700;
                color: var(--livelo-azul);
                margin: 0;
                line-height: 1;
            }}
            
            .metric-label {{
                color: var(--text-secondary);
                font-size: 0.75rem;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-top: 2px;
            }}
            
            .metric-change {{
                font-size: 0.7rem;
                margin-top: 3px;
            }}
            
            .nav-pills .nav-link.active {{ background-color: var(--livelo-rosa); }}
            .nav-pills .nav-link {{ 
                color: var(--livelo-azul); 
                padding: 8px 16px;
                margin-right: 5px;
                border-radius: 20px;
                font-size: 0.9rem;
            }}
            
            .table-container {{
                background: var(--bg-card);
                border-radius: 12px;
                overflow: hidden;
                max-height: 70vh;
                overflow-y: auto;
                overflow-x: auto;
            }}
            
            .table {{ 
                margin: 0; 
                font-size: 0.85rem;
                white-space: nowrap;
                min-width: 100%;
            }}
            
            .table th {{
                background-color: var(--livelo-azul) !important;
                color: white !important;
                border: none !important;
                padding: 12px 8px !important;
                font-weight: 600 !important;
                position: sticky !important;
                top: 0 !important;
                z-index: 10 !important;
                font-size: 0.8rem !important;
                cursor: pointer !important;
                user-select: none !important;
                transition: all 0.2s ease !important;
                text-align: center !important;
                vertical-align: middle !important;
                white-space: nowrap !important;
                min-width: 100px;
            }}
            
            .table th:hover {{ 
                background-color: var(--livelo-rosa) !important;
                transform: translateY(-1px);
            }}
            
            .table td {{
                padding: 8px !important;
                border-bottom: 1px solid var(--border-color) !important;
                vertical-align: middle !important;
                font-size: 0.8rem !important;
                white-space: nowrap !important;
                text-align: center !important;
                background: var(--bg-card) !important;
                color: var(--text-primary) !important;
            }}
            
            .table tbody tr:hover {{ 
                background-color: rgba(255, 10, 140, 0.05) !important; 
            }}
            
            .table td:first-child {{
                text-align: left !important;
                font-weight: 500;
                max-width: 200px;
                overflow: hidden;
                text-overflow: ellipsis;
            }}
            
            /* COLUNA DE FAVORITOS NA TABELA */
            .table td:nth-child(2) {{
                text-align: center !important;
                width: 50px !important;
                min-width: 50px !important;
                max-width: 50px !important;
            }}
            
            .badge-status {{
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 0.7rem;
                font-weight: 500;
                min-width: 60px;
                text-align: center;
                white-space: nowrap;
            }}
            
            /* BADGES SUAVES PARA MELHOR CONTRASTE */
            .badge-soft {{
                display: inline-block;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 0.75rem;
                font-weight: 500;
                text-align: center;
                white-space: nowrap;
                border: 1px solid transparent;
                transition: all 0.2s ease;
            }}
            
            .badge-soft:hover {{
                transform: translateY(-1px);
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            
            /* MODO ESCURO - MELHORAR BADGES */
            [data-theme="dark"] .badge-soft {{
                border: 1px solid rgba(255,255,255,0.1);
                filter: brightness(1.1);
            }}
            
            [data-theme="dark"] .badge-soft:hover {{
                filter: brightness(1.2);
            }}
            
            .search-input {{
                border-radius: 20px;
                border: 2px solid var(--border-color);
                padding: 8px 15px;
                font-size: 0.9rem;
                background: var(--bg-card);
                color: var(--text-primary);
            }}
            
            .search-input:focus {{
                border-color: var(--livelo-rosa);
                box-shadow: 0 0 0 0.2rem rgba(255, 10, 140, 0.25);
                background: var(--bg-card);
                color: var(--text-primary);
            }}
            
            .btn-download {{
                background: linear-gradient(135deg, var(--livelo-rosa) 0%, var(--livelo-azul) 100%);
                border: none;
                border-radius: 20px;
                color: white;
                padding: 8px 20px;
                font-weight: 500;
                font-size: 0.9rem;
            }}
            
            .btn-download:hover {{ 
                color: white; 
                transform: translateY(-1px); 
            }}
            
            .individual-analysis {{
                background: var(--bg-secondary);
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 20px;
            }}
            
            .sort-indicator {{
                margin-left: 5px;
                opacity: 0.3;
                transition: all 0.2s ease;
            }}
            
            .sort-indicator.active {{ 
                opacity: 1; 
                color: #FFD700 !important;
            }}
            
            .table th:hover .sort-indicator {{
                opacity: 0.7;
                color: #FFD700 !important;
            }}
            
            .table-responsive {{ 
                border-radius: 12px; 
            }}
            
            .plotly {{ 
                width: 100% !important; 
            }}
            
            /* Melhorias para gráficos */
            .card .plotly-graph-div {{
                border-radius: 8px;
            }}
            
            [data-theme="dark"] .plotly {{
                background: transparent !important;
            }}
            
            [data-theme="dark"] .plotly .bg {{
                fill: transparent !important;
            }}
            
            /* MELHORAR LEGIBILIDADE DOS GRÁFICOS EM MOBILE */
            @media (max-width: 768px) {{
                .card .plotly-graph-div {{
                    min-height: 300px;
                }}
                
                .plotly .main-svg {{
                    overflow: visible !important;
                }}
            }}
            
            .footer {{
                text-align: center;
                margin-top: 40px;
                padding: 20px;
                color: var(--text-secondary);
                font-size: 0.9rem;
                border-top: 1px solid var(--border-color);
            }}
            
            .footer small {{
                cursor: pointer;
                transition: all 0.2s ease;
            }}
            
            .footer small:hover {{
                color: var(--livelo-azul);
            }}
            
            /* LOGO DO PARCEIRO NA ANÁLISE INDIVIDUAL */
            .logo-parceiro {{
                max-width: 80px;
                max-height: 50px;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                background: white;
                padding: 5px;
                margin-right: 15px;
            }}
            
            /* MOBILE RESPONSIVENESS */
            @media (max-width: 768px) {{
                .theme-toggle {{
                    top: 10px;
                    right: 10px;
                    width: 40px;
                    height: 40px;
                }}
                
                .theme-toggle i {{
                    font-size: 1rem;
                }}
                
                .notification-toggle {{
                    top: 60px;
                    right: 10px;
                    width: 40px;
                    height: 40px;
                }}
                
                .notification-status {{
                    top: 110px;
                    right: 10px;
                }}
                
                .container-fluid {{ 
                    padding: 5px 8px; 
                }}
                
                .metric-value {{ 
                    font-size: 1.4rem; 
                }}
                
                .metric-label {{
                    font-size: 0.65rem;
                }}
                
                .alert-compact {{
                    margin-bottom: 8px;
                }}
                
                .alert-header {{
                    padding: 10px 12px;
                }}
                
                .alert-preview {{
                    padding: 0 12px 10px 12px;
                }}
                
                .partners-grid {{
                    gap: 3px;
                }}
                
                .partner-tag, .lost-tag {{
                    font-size: 0.65rem;
                    padding: 2px 6px;
                }}
                
                .table {{ 
                    font-size: 0.7rem; 
                }}
                
                .table th {{
                    padding: 8px 4px !important;
                    font-size: 0.7rem !important;
                    min-width: 80px;
                }}
                
                .table td {{
                    padding: 6px 4px !important;
                    font-size: 0.7rem !important;
                }}
                
                .nav-pills .nav-link {{ 
                    padding: 6px 10px; 
                    font-size: 0.75rem; 
                    margin-right: 2px;
                }}
                
                .card {{
                    margin-bottom: 10px;
                }}
                
                .individual-analysis {{
                    padding: 15px;
                }}
                
                .btn-download {{
                    font-size: 0.8rem;
                    padding: 6px 15px;
                }}
                
                .row.g-2 {{
                    margin: 0 -2px;
                }}
                
                .row.g-2 > * {{
                    padding-right: 2px;
                    padding-left: 2px;
                }}
                
                .table-container {{
                    max-height: 60vh;
                }}
                
                .metric-card {{
                    padding: 10px;
                }}
                
                .logo-parceiro {{
                    max-width: 60px;
                    max-height: 40px;
                    margin-right: 10px;
                }}
            }}
            
            @media (max-width: 576px) {{
                .table th {{
                    min-width: 70px;
                    padding: 6px 3px !important;
                    font-size: 0.65rem !important;
                }}
                
                .table td {{
                    padding: 5px 3px !important;
                    font-size: 0.65rem !important;
                }}
                
                .nav-pills .nav-link {{
                    font-size: 0.7rem;
                    padding: 5px 8px;
                }}
                
                .metric-value {{
                    font-size: 1.2rem;
                }}
                
                .card-header h6 {{
                    font-size: 0.9rem;
                }}
            }}
            
            /* Melhor scroll em dispositivos touch */
            .table-container {{
                -webkit-overflow-scrolling: touch;
                scrollbar-width: thin;
            }}
            
            .table-container::-webkit-scrollbar {{
                width: 6px;
                height: 6px;
            }}
            
            .table-container::-webkit-scrollbar-track {{
                background: var(--bg-primary);
                border-radius: 3px;
            }}
            
            .table-container::-webkit-scrollbar-thumb {{
                background: var(--livelo-azul-claro);
                border-radius: 3px;
            }}
            
            .table-container::-webkit-scrollbar-thumb:hover {{
                background: var(--livelo-azul);
            }}
        </style>
    </head>
    <body>
        <!-- Theme Toggle -->
        <div class="theme-toggle" onclick="toggleTheme()" title="Alternar tema claro/escuro">
            <i class="bi bi-sun-fill" id="theme-icon"></i>
        </div>
        
        <!-- Notification Toggle -->
        <div class="notification-toggle" onclick="toggleNotifications()" title="Gerenciar notificações">
            <i class="bi bi-bell" id="notification-icon"></i>
        </div>
        
        <!-- Notification Status -->
        <div class="notification-status" id="notificationStatus">
            Carregando...
        </div>
        
        <!-- Notification Banner -->
        <div class="notification-banner" id="notificationBanner">
            <span id="bannerText">🔔 Ative as notificações para receber alertas das suas ofertas favoritas!</span>
            <button onclick="enableNotifications()">Ativar</button>
            <button onclick="dismissBanner()">Agora não</button>
        </div>
        
        <div class="container-fluid">
            <!-- Header -->
            <div class="text-center mb-3">
                <h1 class="h3 fw-bold mb-1" style="color: var(--livelo-azul);">
                    <i class="bi bi-graph-up me-2"></i>Livelo Analytics Pro
                </h1>
                <small class="text-muted">Atualizado em {metricas['ultima_atualizacao']} | {metricas['total_parceiros']} parceiros no site hoje</small><br>
                <small class="text-muted" style="font-size: 0.75rem;">Dados coletados em: {metricas['data_coleta_mais_recente']}</small>
            </div>
            
            <!-- Alertas Dinâmicos Compactos + INTELIGENTES -->
            {alertas_html}
            
            <!-- Métricas Principais -->
            <div class="row g-2 mb-3">
                <div class="col-lg-2 col-md-4 col-6">
                    <div class="metric-card text-center">
                        <div class="metric-value">{metricas['total_parceiros']}</div>
                        <div class="metric-label">Parceiros Hoje</div>
                        <div class="metric-change" style="color: {'green' if metricas['variacao_parceiros'] >= 0 else 'red'};">
                            {'+' if metricas['variacao_parceiros'] > 0 else ''}{metricas['variacao_parceiros']} vs ontem
                        </div>
                    </div>
                </div>
                <div class="col-lg-2 col-md-4 col-6">
                    <div class="metric-card text-center">
                        <div class="metric-value">{metricas['total_com_oferta']}</div>
                        <div class="metric-label">Com Oferta</div>
                        <div class="metric-change" style="color: {'green' if metricas['variacao_ofertas'] >= 0 else 'red'};">
                            {'+' if metricas['variacao_ofertas'] > 0 else ''}{metricas['variacao_ofertas']} vs ontem
                        </div>
                    </div>
                </div>
                <div class="col-lg-2 col-md-4 col-6">
                    <div class="metric-card text-center">
                        <div class="metric-value">{metricas['percentual_ofertas_hoje']:.1f}%</div>
                        <div class="metric-label">% Ofertas</div>
                        <div class="metric-change">
                            {metricas['percentual_ofertas_ontem']:.1f}% ontem
                        </div>
                    </div>
                </div>
                <div class="col-lg-2 col-md-4 col-6">
                    <div class="metric-card text-center">
                        <div class="metric-value">{metricas['compre_agora']}</div>
                        <div class="metric-label">Compre Agora!</div>
                        <div class="metric-change text-success">
                            Oportunidades hoje
                        </div>
                    </div>
                </div>
                <div class="col-lg-2 col-md-4 col-6">
                    <div class="metric-card text-center">
                        <div class="metric-value">{metricas['oportunidades_raras']}</div>
                        <div class="metric-label">Oport. Raras</div>
                        <div class="metric-change text-warning">
                            Baixa frequência
                        </div>
                    </div>
                </div>
                <div class="col-lg-2 col-md-4 col-6">
                    <div class="metric-card text-center">
                        <div class="metric-value">{metricas['sempre_oferta']}</div>
                        <div class="metric-label">Sempre Oferta</div>
                        <div class="metric-change text-info">
                            Qualquer hora
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Navegação COM NOVA ABA -->
            <ul class="nav nav-pills justify-content-center mb-3" id="mainTabs" role="tablist">
                <li class="nav-item">
                    <button class="nav-link active" data-bs-toggle="pill" data-bs-target="#dashboard">
                        <i class="bi bi-speedometer2 me-1"></i>Dashboard
                    </button>
                </li>
                <li class="nav-item">
                    <button class="nav-link" data-bs-toggle="pill" data-bs-target="#analise">
                        <i class="bi bi-table me-1"></i>Análise Completa
                    </button>
                </li>
                <li class="nav-item">
                    <button class="nav-link" data-bs-toggle="pill" data-bs-target="#carteira">
                        <i class="bi bi-star me-1"></i>Minha Carteira
                    </button>
                </li>
                <li class="nav-item">
                    <button class="nav-link" data-bs-toggle="pill" data-bs-target="#individual">
                        <i class="bi bi-person-check me-1"></i>Análise Individual
                    </button>
                </li>
            </ul>
            
            <div class="tab-content">
                <!-- Dashboard -->
                <div class="tab-pane fade show active" id="dashboard">
                    <!-- LINHA 1: Gráfico Principal Temporal COM CONTROLES -->
                    <div class="row g-3 mb-3">
                        <div class="col-12">
                            <div class="card">
                                <div class="card-header"><h6 class="mb-0">📈 Evolução Temporal - Visão Estratégica</h6></div>
                                <div class="card-body p-2">
                                    {self._gerar_controles_evolucao_temporal()}
                                    {graficos_html.get('evolucao_temporal', '<p>Carregando dados temporais...</p>')}
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- LINHA 2: Análise Estratégica (2 médios) -->
                    <div class="row g-3 mb-3">
                        <div class="col-lg-6">
                            <div class="card">
                                <div class="card-header"><h6 class="mb-0">💎 Matriz de Oportunidades</h6></div>
                                <div class="card-body p-2">{graficos_html.get('matriz_oportunidades', '<p>Matriz não disponível</p>')}</div>
                            </div>
                        </div>
                        <div class="col-lg-6">
                            <div class="card">
                                <div class="card-header"><h6 class="mb-0">🏆 Top 10 Categorias</h6></div>
                                <div class="card-body p-2">{graficos_html.get('top_categorias', '<p>Top categorias não disponível</p>')}</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- LINHA 3: Performance Atual (3 compactos) -->
                    <div class="row g-3 mb-3">
                        <div class="col-lg-4">
                            <div class="card">
                                <div class="card-header"><h6 class="mb-0">🥇 Top 10 Ofertas</h6></div>
                                <div class="card-body p-2">{graficos_html.get('top_ofertas', '<p>Top ofertas não disponível</p>')}</div>
                            </div>
                        </div>
                        <div class="col-lg-4">
                            <div class="card">
                                <div class="card-header"><h6 class="mb-0">⚡ Mudanças Hoje</h6></div>
                                <div class="card-body p-2">{graficos_html.get('mudancas_hoje', '<p>Sem mudanças detectadas</p>')}</div>
                            </div>
                        </div>
                        <div class="col-lg-4">
                            <div class="card">
                                <div class="card-header"><h6 class="mb-0">⏰ Tempo de Casa</h6></div>
                                <div class="card-body p-2">{graficos_html.get('tempo_casa', '<p>Tempo de casa não disponível</p>')}</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- LINHA 4: Insights Avançados (2 médios) -->
                    <div class="row g-3">
                        <div class="col-lg-6">
                            <div class="card">
                                <div class="card-header"><h6 class="mb-0">📊 Tendência Semanal</h6></div>
                                <div class="card-body p-2">{graficos_html.get('tendencia_semanal', '<p>Tendência não disponível</p>')}</div>
                            </div>
                        </div>
                        <div class="col-lg-6">
                            <div class="card">
                                <div class="card-header"><h6 class="mb-0">🎨 Mapa de Categorias</h6></div>
                                <div class="card-body p-2">{graficos_html.get('mapa_categorias', '<p>Mapa não disponível</p>')}</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Análise Completa -->
                <div class="tab-pane fade" id="analise">
                    <!-- Filtros Avançados -->
                    {filtros_html}
                    
                    <!-- BOTÃO RESET FILTROS TEMPORAIS -->
                    <div class="mb-3">
                        <div class="row align-items-center">
                            <div class="col-auto">
                                <strong class="text-muted">Filtros Temporais:</strong>
                            </div>
                            <div class="col-auto">
                                <button class="btn btn-outline-danger btn-sm" onclick="resetarFiltrosTemporaisCompleta()" title="Resetar todos os filtros temporais">
                                    <i class="bi bi-arrow-clockwise me-1"></i>Reset Filtros Temporais
                                </button>
                            </div>
                            <div class="col-auto">
                                <small class="text-muted">Para gráfico da evolução temporal</small>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h6 class="mb-0">Análise Completa - {metricas['total_parceiros']} Parceiros HOJE</h6>
                            <button class="btn btn-download btn-sm" onclick="downloadAnaliseCompleta()">
                                <i class="bi bi-download me-1"></i>Download Excel
                            </button>
                        </div>
                        <div class="card-body p-0">
                            <div class="p-3 border-bottom">
                                <input type="text" class="form-control search-input" id="searchInput" placeholder="🔍 Buscar parceiro...">
                            </div>
                            <div class="table-responsive table-container">
                                {self._gerar_tabela_analise_completa_com_favoritos(dados)}
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- NOVA ABA: MINHA CARTEIRA -->
                <div class="tab-pane fade" id="carteira">
                    <div class="row">
                        <div class="col-lg-8">
                            <div class="card">
                                <div class="card-header d-flex justify-content-between align-items-center">
                                    <h6 class="mb-0"><i class="bi bi-star-fill me-2" style="color: #ffc107;"></i>Minha Carteira - <span id="contadorFavoritos">0</span> Favoritos</h6>
                                    <button class="btn btn-outline-danger btn-sm" onclick="limparCarteira()" title="Limpar todos os favoritos">
                                        <i class="bi bi-trash me-1"></i>Limpar Carteira
                                    </button>
                                </div>
                                <div class="card-body">
                                    <div id="listaFavoritos">
                                        <!-- Preenchido pelo JavaScript -->
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="col-lg-4">
                            <div class="card">
                                <div class="card-header">
                                    <h6 class="mb-0">📊 Evolução da Carteira</h6>
                                </div>
                                <div class="card-body">
                                    <div id="graficoCarteira">
                                        <!-- Gráfico da carteira -->
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Análise Individual -->
                <div class="tab-pane fade" id="individual">
                    <div class="individual-analysis">
                        <div class="row align-items-center mb-3">
                            <div class="col-md-6">
                                <label class="form-label fw-bold">Selecionar Parceiro:</label>
                                <select class="form-select" id="parceiroSelect" onchange="carregarAnaliseIndividual()">
                                    {self._gerar_opcoes_parceiros(dados)}
                                </select>
                            </div>
                            <div class="col-md-6 text-end">
                                <button class="btn btn-download" onclick="downloadAnaliseIndividual()">
                                    <i class="bi bi-download me-1"></i>Download Parceiro
                                </button>
                            </div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            <h6 class="mb-0" id="tituloAnaliseIndividual">Histórico Detalhado</h6>
                        </div>
                        <div class="card-body p-0">
                            <div class="table-responsive table-container">
                                <div id="tabelaIndividual">Selecione um parceiro para ver o histórico...</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- RESUMO ESTATÍSTICO SERÁ ADICIONADO AQUI PELO JAVASCRIPT (FORA DA TABELA) -->
                </div>
            </div>
            
            <!-- Rodapé -->
            <div class="footer">
                <small onclick="downloadDadosRaw()" title="Download dados brutos">Desenvolvido por gc</small>
            </div>
        </div>
        
        <script>
            // Dados para análise
            const todosOsDados = {dados_json};
            const dadosHistoricosCompletos = {dados_historicos_json};
            const dadosRawCompletos = {dados_raw_json};
            let parceiroSelecionado = null;
            
            // ========== SISTEMA DE NOTIFICAÇÕES FIREBASE ==========
            let isNotificationsEnabled = false;
            let notificationToken = null;
            
            // Verificar se notificações estão suportadas
            function isNotificationSupported() {{
                return 'Notification' in window && 'serviceWorker' in navigator;
            }}
            
            // Configurar Firebase Messaging (chamado após inicialização)
            async function initializeNotifications() {{
                if (!isNotificationSupported()) {{
                    updateNotificationStatus('Não suportado');
                    return;
                }}
                
                updateNotificationStatus('Carregando...');
                
                try {{
                    // Verificar se Firebase está disponível
                    if (!window.firebaseMessaging) {{
                        console.warn('Firebase não inicializado');
                        updateNotificationStatus('Firebase indisponível');
                        return;
                    }}
                    
                    // Registrar service worker
                    const registration = await navigator.serviceWorker.register('/sw.js');
                    console.log('Service Worker registrado:', registration);
                    
                    // Verificar permissão atual
                    const permission = Notification.permission;
                    
                    if (permission === 'granted') {{
                        await setupMessaging();
                    }} else if (permission === 'default') {{
                        updateNotificationStatus('Clique no sino para ativar');
                        showNotificationBanner();
                    }} else {{
                        updateNotificationStatus('Bloqueadas pelo navegador');
                    }}
                    
                }} catch (error) {{
                    console.error('Erro ao inicializar notificações:', error);
                    updateNotificationStatus('Erro na inicialização');
                }}
            }}
            
            // Configurar Firebase Messaging
            async function setupMessaging() {{
                try {{
                    const {{ getToken, onMessage }} = await import('https://www.gstatic.com/firebasejs/9.23.0/firebase-messaging.js');
                    
                    // Obter token FCM
                    const currentToken = await getToken(window.firebaseMessaging, {{
                        vapidKey: 'YOUR_VAPID_KEY_HERE' // Será substituído automaticamente
                    }});
                    
                    if (currentToken) {{
                        notificationToken = currentToken;
                        console.log('Token FCM obtido:', currentToken);
                        
                        // Salvar token no localStorage para envio posterior
                        localStorage.setItem('fcm-token', currentToken);
                        localStorage.setItem('fcm-token-timestamp', Date.now().toString());
                        
                        isNotificationsEnabled = true;
                        updateNotificationStatus('Ativas');
                        updateNotificationIcon();
                        dismissBanner();
                        
                        // Configurar listener para mensagens em foreground
                        onMessage(window.firebaseMessaging, (payload) => {{
                            console.log('Mensagem recebida em foreground:', payload);
                            showInAppNotification(payload);
                        }});
                        
                    }} else {{
                        console.log('Nenhum token disponível');
                        updateNotificationStatus('Falha ao obter token');
                    }}
                    
                }} catch (error) {{
                    console.error('Erro ao configurar messaging:', error);
                    updateNotificationStatus('Erro na configuração');
                }}
            }}
            
            // Solicitar permissão para notificações
            async function enableNotifications() {{
                try {{
                    const permission = await Notification.requestPermission();
                    
                    if (permission === 'granted') {{
                        await setupMessaging();
                    }} else {{
                        updateNotificationStatus('Permissão negada');
                        console.log('Permissão de notificação negada');
                    }}
                    
                }} catch (error) {{
                    console.error('Erro ao solicitar permissão:', error);
                    updateNotificationStatus('Erro na permissão');
                }}
            }}
            
            // Toggle de notificações
            async function toggleNotifications() {{
                if (!isNotificationSupported()) {{
                    alert('Notificações não são suportadas neste navegador');
                    return;
                }}
                
                const permission = Notification.permission;
                
                if (permission === 'default') {{
                    await enableNotifications();
                }} else if (permission === 'denied') {{
                    alert('Notificações foram bloqueadas. Habilite nas configurações do navegador.');
                }} else if (permission === 'granted') {{
                    // Alternar entre ativo/inativo
                    isNotificationsEnabled = !isNotificationsEnabled;
                    localStorage.setItem('notifications-enabled', isNotificationsEnabled.toString());
                    updateNotificationStatus(isNotificationsEnabled ? 'Ativas' : 'Pausadas');
                    updateNotificationIcon();
                }}
            }}
            
            // Atualizar ícone de notificação
            function updateNotificationIcon() {{
                const icon = document.getElementById('notification-icon');
                const toggle = document.querySelector('.notification-toggle');
                
                if (isNotificationsEnabled) {{
                    icon.className = 'bi bi-bell-fill';
                    toggle.classList.add('active');
                }} else {{
                    icon.className = 'bi bi-bell';
                    toggle.classList.remove('active');
                }}
            }}
            
            // Atualizar status de notificação
            function updateNotificationStatus(status) {{
                const statusElement = document.getElementById('notificationStatus');
                statusElement.textContent = status;
                
                // Mostrar temporariamente
                statusElement.classList.add('show');
                setTimeout(() => {{
                    statusElement.classList.remove('show');
                }}, 3000);
            }}
            
            // Mostrar banner de notificação
            function showNotificationBanner() {{
                const banner = document.getElementById('notificationBanner');
                banner.classList.add('show');
            }}
            
            // Dispensar banner
            function dismissBanner() {{
                const banner = document.getElementById('notificationBanner');
                banner.classList.remove('show');
                localStorage.setItem('notification-banner-dismissed', 'true');
            }}
            
                            // Mostrar notificação in-app (quando app está em foreground)
            function showInAppNotification(payload) {{
                const notification = document.createElement('div');
                notification.className = 'alert alert-info position-fixed';
                notification.style.cssText = `
                    top: 20px;
                    right: 20px;
                    z-index: 1050;
                    max-width: 300px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                `;
                
                notification.innerHTML = `
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <strong>${{payload.notification?.title || 'Livelo Analytics'}}</strong>
                            <div class="small mt-1">${{payload.notification?.body || 'Nova atualização disponível'}}</div>
                        </div>
                        <button type="button" class="btn-close btn-close-white" onclick="this.parentElement.parentElement.remove()"></button>
                    </div>
                `;
                
                document.body.appendChild(notification);
                
                // Remover automaticamente após 5 segundos
                setTimeout(() => {{
                    if (notification.parentElement) {{
                        notification.remove();
                    }}
                }}, 5000);
            }}
            
            // Verificar favoritos com ofertas (chamado periodicamente)
            function checkFavoritesWithOffers() {{
                const favoritos = JSON.parse(localStorage.getItem('livelo-favoritos') || '[]');
                const favoritosComOferta = [];
                
                favoritos.forEach(chaveUnica => {{
                    const [parceiro, moeda] = chaveUnica.split('|');
                    const dados = todosOsDados.find(item => item.Parceiro === parceiro && item.Moeda === moeda);
                    
                    if (dados && dados.Tem_Oferta_Hoje) {{
                        favoritosComOferta.push({{
                            parceiro: parceiro,
                            moeda: moeda,
                            pontos: dados.Pontos_por_Moeda_Atual
                        }});
                    }}
                }});
                
                // Salvar no localStorage para verificação pelo servidor
                localStorage.setItem('favoritos-com-oferta', JSON.stringify(favoritosComOferta));
                
                return favoritosComOferta;
            }}
            
            // ========== SISTEMA DE FAVORITOS - MINHA CARTEIRA ==========
            let favoritos = JSON.parse(localStorage.getItem('livelo-favoritos') || '[]');
            
            function toggleFavorito(parceiro, moeda) {{
                const chaveUnica = `${{parceiro}}|${{moeda}}`;
                const index = favoritos.indexOf(chaveUnica);
                
                if (index === -1) {{
                    if (favoritos.length < 10) {{
                        favoritos.push(chaveUnica);
                    }} else {{
                        alert('Máximo de 10 favoritos! Remova algum para adicionar novo.');
                        return;
                    }}
                }} else {{
                    favoritos.splice(index, 1);
                }}
                
                localStorage.setItem('livelo-favoritos', JSON.stringify(favoritos));
                atualizarIconesFavoritos();
                atualizarCarteira();
                
                // Verificar se algum favorito tem oferta
                checkFavoritesWithOffers();
            }}
            
            function atualizarIconesFavoritos() {{
                document.querySelectorAll('.favorito-btn').forEach(btn => {{
                    const parceiro = btn.dataset.parceiro;
                    const moeda = btn.dataset.moeda;
                    const chaveUnica = `${{parceiro}}|${{moeda}}`;
                    
                    if (favoritos.includes(chaveUnica)) {{
                        btn.classList.add('ativo');
                        btn.innerHTML = '<i class="bi bi-star-fill"></i>';
                    }} else {{
                        btn.classList.remove('ativo');
                        btn.innerHTML = '<i class="bi bi-star"></i>';
                    }}
                }});
            }}
            
            function atualizarCarteira() {{
                const container = document.getElementById('listaFavoritos');
                const contador = document.getElementById('contadorFavoritos');
                
                contador.textContent = favoritos.length;
                
                if (favoritos.length === 0) {{
                    container.innerHTML = `
                        <div class="carteira-vazia">
                            <i class="bi bi-star" style="font-size: 3rem; color: #ccc; margin-bottom: 15px; display: block;"></i>
                            <h6>Sua carteira está vazia</h6>
                            <p class="text-muted">Clique na estrela ⭐ ao lado dos parceiros na tabela para adicioná-los aos favoritos.</p>
                            <small class="text-muted">Máximo: 10 favoritos</small>
                        </div>
                    `;
                    document.getElementById('graficoCarteira').innerHTML = '<p class="text-center text-muted mt-5">Adicione favoritos para ver o gráfico</p>';
                    return;
                }}
                
                let html = '';
                const favoritosData = [];
                
                favoritos.forEach(chaveUnica => {{
                    const [parceiro, moeda] = chaveUnica.split('|');
                    const dados = todosOsDados.find(item => item.Parceiro === parceiro && item.Moeda === moeda);
                    
                    if (dados) {{
                        favoritosData.push(dados);
                        const temOferta = dados.Tem_Oferta_Hoje;
                        const statusClass = temOferta ? 'text-success' : 'text-muted';
                        const statusIcon = temOferta ? 'bi-check-circle-fill' : 'bi-circle';
                        
                        html += `
                            <div class="carteira-item">
                                <div>
                                    <div class="carteira-nome">${{parceiro}} (${{moeda}})</div>
                                    <div class="carteira-info">
                                        <i class="bi ${{statusIcon}} ${{statusClass}} me-1"></i>
                                        ${{temOferta ? 'Com oferta hoje' : 'Sem oferta hoje'}} • 
                                        ${{dados.Categoria_Dimensao}} • Tier ${{dados.Tier}}
                                    </div>
                                </div>
                                <div class="text-end">
                                    <div class="carteira-pontos">${{dados.Pontos_por_Moeda_Atual.toFixed(1)}} pts</div>
                                    <button class="btn btn-sm btn-outline-danger" onclick="removerFavorito('${{chaveUnica}}')" title="Remover">
                                        <i class="bi bi-x"></i>
                                    </button>
                                </div>
                            </div>
                        `;
                    }}
                }});
                
                container.innerHTML = html;
                gerarGraficoCarteira(favoritosData);
            }}
            
            function removerFavorito(chaveUnica) {{
                favoritos = favoritos.filter(f => f !== chaveUnica);
                localStorage.setItem('livelo-favoritos', JSON.stringify(favoritos));
                atualizarIconesFavoritos();
                atualizarCarteira();
                checkFavoritesWithOffers();
            }}
            
            function limparCarteira() {{
                if (confirm('Tem certeza que deseja limpar toda a carteira?')) {{
                    favoritos = [];
                    localStorage.setItem('livelo-favoritos', JSON.stringify(favoritos));
                    atualizarIconesFavoritos();
                    atualizarCarteira();
                    checkFavoritesWithOffers();
                }}
            }}
            
            function gerarGraficoCarteira(favoritosData) {{
                if (favoritosData.length === 0) return;
                
                // Gráfico simples de barras dos favoritos
                const container = document.getElementById('graficoCarteira');
                let html = '<div class="mb-3"><strong>Pontos por Moeda Atual:</strong></div>';
                
                favoritosData.sort((a, b) => b.Pontos_por_Moeda_Atual - a.Pontos_por_Moeda_Atual);
                
                favoritosData.forEach(dados => {{
                    const largura = (dados.Pontos_por_Moeda_Atual / favoritosData[0].Pontos_por_Moeda_Atual) * 100;
                    const cor = dados.Tem_Oferta_Hoje ? '#28a745' : '#6c757d';
                    
                    html += `
                        <div class="mb-2">
                            <div class="d-flex justify-content-between align-items-center mb-1">
                                <small class="fw-bold">${{dados.Parceiro}}</small>
                                <small class="text-muted">${{dados.Pontos_por_Moeda_Atual.toFixed(1)}} pts</small>
                            </div>
                            <div class="progress" style="height: 8px;">
                                <div class="progress-bar" style="width: ${{largura}}%; background-color: ${{cor}};"></div>
                            </div>
                        </div>
                    `;
                }});
                
                container.innerHTML = html;
            }}
            
            // RESET FILTROS TEMPORAIS PARA ABA ANÁLISE COMPLETA
            function resetarFiltrosTemporaisCompleta() {{
                const filtroMes = document.getElementById('filtroMes');
                const filtroAno = document.getElementById('filtroAno');
                
                if (filtroMes) filtroMes.value = '';
                if (filtroAno) filtroAno.value = '';
                
                if (typeof aplicarFiltrosTemporal === 'function') {{
                    aplicarFiltrosTemporal();
                }}
                
                const btn = event.target.closest('button');
                const originalText = btn.innerHTML;
                btn.innerHTML = '<i class="bi bi-check me-1"></i>Resetado!';
                btn.classList.remove('btn-outline-danger');
                btn.classList.add('btn-success');
                
                setTimeout(() => {{
                    btn.innerHTML = originalText;
                    btn.classList.remove('btn-success');
                    btn.classList.add('btn-outline-danger');
                }}, 1500);
            }}
            
            // GERENCIAMENTO DE TEMA
            function initTheme() {{
                const savedTheme = localStorage.getItem('livelo-theme') || 'light';
                document.documentElement.setAttribute('data-theme', savedTheme);
                updateThemeIcon(savedTheme);
            }}
            
            function toggleTheme() {{
                const currentTheme = document.documentElement.getAttribute('data-theme');
                const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
                document.documentElement.setAttribute('data-theme', newTheme);
                localStorage.setItem('livelo-theme', newTheme);
                updateThemeIcon(newTheme);
            }}
            
            function updateThemeIcon(theme) {{
                const icon = document.getElementById('theme-icon');
                if (theme === 'dark') {{
                    icon.className = 'bi bi-moon-fill';
                }} else {{
                    icon.className = 'bi bi-sun-fill';
                }}
            }}
            
            // GERENCIAMENTO DE ALERTAS
            function toggleAlert(alertId) {{
                const alert = document.querySelector(`[data-alert-id="${{alertId}}"]`);
                if (!alert) return;
                
                const details = alert.querySelector('.alert-details');
                const chevron = alert.querySelector('.alert-chevron');
                
                if (details.style.display === 'none' || details.style.display === '') {{
                    details.style.display = 'block';
                    alert.classList.add('expanded');
                }} else {{
                    details.style.display = 'none';
                    alert.classList.remove('expanded');
                }}
            }}
            
            function closeAlert(alertId, event) {{
                event.stopPropagation();
                const alert = document.querySelector(`[data-alert-id="${{alertId}}"]`);
                if (alert) {{
                    alert.style.animation = 'slideUp 0.3s ease';
                    setTimeout(() => {{
                        alert.remove();
                    }}, 300);
                }}
            }}
            
            // Animação de slide up para fechar alertas
            const slideUpKeyframes = `
                @keyframes slideUp {{
                    from {{
                        opacity: 1;
                        max-height: 200px;
                        transform: translateY(0);
                    }}
                    to {{
                        opacity: 0;
                        max-height: 0;
                        transform: translateY(-10px);
                    }}
                }}
            `;
            const style = document.createElement('style');
            style.textContent = slideUpKeyframes;
            document.head.appendChild(style);
            
            // ========== FILTROS TEMPORAIS - JAVASCRIPT ==========
            
            // Dados originais do gráfico
            let dadosOriginais = null;
            let graficoEvolucaoPlot = null;
            
            // Inicializar filtros temporais após carregamento do DOM
            function inicializarFiltrosTemporal() {{
                try {{
                    // Buscar o gráfico pelo div que contém o plotly
                    const plotlyDivs = document.querySelectorAll('.plotly-graph-div');
                    for (let div of plotlyDivs) {{
                        if (div.closest('.card-body')) {{
                            const cardHeader = div.closest('.card').querySelector('.card-header h6');
                            if (cardHeader && cardHeader.textContent.includes('Evolução Temporal')) {{
                                graficoEvolucaoPlot = div;
                                break;
                            }}
                        }}
                    }}
                    
                    if (graficoEvolucaoPlot && window.dadosEvolucaoTemporal) {{
                        dadosOriginais = window.dadosEvolucaoTemporal;
                        console.log('Filtros temporais inicializados com', dadosOriginais.length, 'registros');
                        
                        // Interceptar cliques nos botões de range
                        interceptarBotoesRange();
                    }}
                }} catch (error) {{
                    console.error('Erro ao inicializar filtros temporais:', error);
                }}
            }}
            
            function interceptarBotoesRange() {{
                // Aguardar os botões serem criados pelo Plotly
                setTimeout(() => {{
                    if (!graficoEvolucaoPlot) return;
                    
                    const botoes = graficoEvolucaoPlot.querySelectorAll('.rangeselector-button');
                    botoes.forEach(botao => {{
                        botao.addEventListener('click', function() {{
                            // Limpar dropdowns quando usar botões de range
                            setTimeout(() => {{
                                const filtroMes = document.getElementById('filtroMes');
                                const filtroAno = document.getElementById('filtroAno');
                                if (filtroMes && filtroAno) {{
                                    filtroMes.value = '';
                                    filtroAno.value = '';
                                    atualizarStatusFiltro();
                                }}
                            }}, 100);
                        }});
                    }});
                }}, 500);
            }}
            
            function aplicarFiltrosTemporal() {{
                if (!dadosOriginais || !graficoEvolucaoPlot) {{
                    console.warn('Dados ou gráfico não disponíveis');
                    return;
                }}
                
                const filtroMes = document.getElementById('filtroMes');
                const filtroAno = document.getElementById('filtroAno');
                
                if (!filtroMes || !filtroAno) {{
                    console.warn('Elementos de filtro não encontrados');
                    return;
                }}
                
                const mesSelecionado = filtroMes.value;
                const anoSelecionado = filtroAno.value;
                
                let dadosFiltrados = dadosOriginais;
                
                // Aplicar filtros
                if (mesSelecionado || anoSelecionado) {{
                    dadosFiltrados = dadosOriginais.filter(item => {{
                        const data = new Date(item.Data);
                        const mes = data.getMonth() + 1; // JavaScript months são 0-indexed
                        const ano = data.getFullYear();
                        
                        let incluir = true;
                        
                        if (mesSelecionado) {{
                            incluir = incluir && (mes == parseInt(mesSelecionado));
                        }}
                        
                        if (anoSelecionado) {{
                            incluir = incluir && (ano == parseInt(anoSelecionado));
                        }}
                        
                        return incluir;
                    }});
                }}
                
                // Preparar dados para atualizar o gráfico
                const datas = dadosFiltrados.map(item => item.Data);
                const parceiros = dadosFiltrados.map(item => item.Total_Parceiros);
                const ofertas = dadosFiltrados.map(item => item.Total_Ofertas);
                
                // Atualizar gráfico usando Plotly.restyle
                const update = {{
                    x: [datas, datas],
                    y: [parceiros, ofertas],
                    text: [parceiros, ofertas]
                }};
                
                try {{
                    Plotly.restyle(graficoEvolucaoPlot, update);
                    
                    // Resetar zoom para mostrar todos os dados filtrados
                    if (dadosFiltrados.length > 0) {{
                        const layout_update = {{
                            'xaxis.autorange': true,
                            'yaxis.range': [0, Math.max(...parceiros, ...ofertas) * 1.15]
                        }};
                        Plotly.relayout(graficoEvolucaoPlot, layout_update);
                    }}
                    
                    atualizarStatusFiltro(dadosFiltrados.length);
                    
                }} catch (error) {{
                    console.error('Erro ao atualizar gráfico:', error);
                }}
            }}
            
            function limparFiltrosTemporal() {{
                const filtroMes = document.getElementById('filtroMes');
                const filtroAno = document.getElementById('filtroAno');
                
                if (filtroMes && filtroAno) {{
                    // Limpar dropdowns
                    filtroMes.value = '';
                    filtroAno.value = '';
                    
                    // Aplicar filtros (que agora mostrará todos os dados)
                    aplicarFiltrosTemporal();
                }}
            }}
            
            function atualizarStatusFiltro(totalRegistros = null) {{
                const filtroMes = document.getElementById('filtroMes');
                const filtroAno = document.getElementById('filtroAno');
                const status = document.getElementById('statusFiltroTemporal');
                
                if (!filtroMes || !filtroAno || !status) return;
                
                const mesSelecionado = filtroMes.value;
                const anoSelecionado = filtroAno.value;
                
                if (!mesSelecionado && !anoSelecionado) {{
                    status.textContent = 'Mostrando todos os dados';
                    status.className = 'filtro-status text-muted';
                }} else {{
                    let textoFiltro = 'Filtrado: ';
                    if (mesSelecionado && anoSelecionado) {{
                        const nomesMeses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 
                                        'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
                        textoFiltro += `${{nomesMeses[parseInt(mesSelecionado)-1]}}/${{anoSelecionado}}`;
                    }} else if (mesSelecionado) {{
                        const nomesMeses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                                        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
                        textoFiltro += `${{nomesMeses[parseInt(mesSelecionado)-1]}} (todos os anos)`;
                    }} else if (anoSelecionado) {{
                        textoFiltro += `${{anoSelecionado}} (ano completo)`;
                    }}
                    
                    if (totalRegistros !== null) {{
                        textoFiltro += ` - ${{totalRegistros}} dias`;
                    }}
                    
                    status.textContent = textoFiltro;
                    status.className = 'filtro-status text-primary fw-bold';
                }}
            }}
            
            // ========== FIM FILTROS TEMPORAIS ==========
            
            // FUNÇÃO AUXILIAR MELHORADA PARA PARSE DE DATAS EM PT-BR
            function parseDataBR(dataString) {{
                if (!dataString || dataString === '-' || dataString === 'Nunca') {{
                    return new Date(1900, 0, 1);
                }}
                
                let cleanDate = dataString.trim();
                let [datePart, timePart] = cleanDate.split(' ');
                
                let year, month, day, hour = 0, minute = 0, second = 0;
                
                if (datePart.includes('/')) {{
                    let [d, m, y] = datePart.split('/');
                    day = parseInt(d);
                    month = parseInt(m) - 1;
                    year = parseInt(y);
                }} else if (datePart.includes('-')) {{
                    let [y, m, d] = datePart.split('-');
                    day = parseInt(d);
                    month = parseInt(m) - 1;
                    year = parseInt(y);
                }} else {{
                    return new Date(dataString);
                }}
                
                if (timePart) {{
                    let timeParts = timePart.split(':');
                    hour = parseInt(timeParts[0]) || 0;
                    minute = parseInt(timeParts[1]) || 0;
                    second = parseInt(timeParts[2]) || 0;
                }}
                
                return new Date(year, month, day, hour, minute, second);
            }}
            
            // FILTROS AVANÇADOS ATUALIZADOS
            function aplicarFiltros() {{
                const filtroCategoria = document.getElementById('filtroCategoriaComplex').value;
                const filtroTier = document.getElementById('filtroTier').value;
                const filtroOferta = document.getElementById('filtroOferta').value;
                const filtroExperiencia = document.getElementById('filtroExperiencia').value;
                const filtroFrequencia = document.getElementById('filtroFrequencia').value;
                const searchTerm = document.getElementById('searchInput').value.toLowerCase();
                
                const rows = document.querySelectorAll('#tabelaAnalise tbody tr');
                
                rows.forEach(row => {{
                    const parceiro = row.cells[0].textContent.toLowerCase();
                    const categoria = row.cells[2].textContent.trim(); // Agora na posição 2 por causa da coluna de favoritos
                    const tier = row.cells[3].textContent.trim();
                    const oferta = row.cells[4].textContent.trim();
                    const experiencia = row.cells[5].textContent.trim();
                    const frequencia = row.cells[6].textContent.trim();
                    
                    const matchParceiro = !searchTerm || parceiro.includes(searchTerm);
                    const matchCategoria = !filtroCategoria || categoria === filtroCategoria;
                    const matchTier = !filtroTier || tier === filtroTier;
                    const matchOferta = !filtroOferta || oferta === filtroOferta;
                    const matchExperiencia = !filtroExperiencia || experiencia === filtroExperiencia;
                    const matchFrequencia = !filtroFrequencia || frequencia === filtroFrequencia;
                    
                    row.style.display = (matchParceiro && matchCategoria && matchTier && matchOferta && matchExperiencia && matchFrequencia) ? '' : 'none';
                }});
            }}
            
            // Busca na tabela
            document.getElementById('searchInput').addEventListener('input', aplicarFiltros);
            
            // Ordenação da tabela principal
            let estadoOrdenacao = {{}};
            
            function ordenarTabela(indiceColuna, tipoColuna) {{
                const tabela = document.querySelector('#tabelaAnalise');
                if (!tabela) return;
                
                const tbody = tabela.querySelector('tbody');
                const linhas = Array.from(tbody.querySelectorAll('tr'));
                
                const estadoAtual = estadoOrdenacao[indiceColuna] || 'neutro';
                let novaOrdem;
                if (estadoAtual === 'neutro' || estadoAtual === 'desc') {{
                    novaOrdem = 'asc';
                }} else {{
                    novaOrdem = 'desc';
                }}
                estadoOrdenacao[indiceColuna] = novaOrdem;
                
                tabela.querySelectorAll('th .sort-indicator').forEach(indicator => {{
                    indicator.className = 'bi bi-arrows-expand sort-indicator';
                }});
                
                const headerAtual = tabela.querySelectorAll('th')[indiceColuna];
                const indicatorAtual = headerAtual.querySelector('.sort-indicator');
                indicatorAtual.className = `bi bi-arrow-${{novaOrdem === 'asc' ? 'up' : 'down'}} sort-indicator active`;
                
                linhas.sort((linhaA, linhaB) => {{
                    let textoA = linhaA.cells[indiceColuna].textContent.trim();
                    let textoB = linhaB.cells[indiceColuna].textContent.trim();
                    
                    const badgeA = linhaA.cells[indiceColuna].querySelector('.badge');
                    const badgeB = linhaB.cells[indiceColuna].querySelector('.badge');
                    if (badgeA) textoA = badgeA.textContent.trim();
                    if (badgeB) textoB = badgeB.textContent.trim();
                    
                    let resultado = 0;
                    
                    if (tipoColuna === 'numero') {{
                        let numA = parseFloat(textoA.replace(/[^\\d.-]/g, '')) || 0;
                        let numB = parseFloat(textoB.replace(/[^\\d.-]/g, '')) || 0;
                        
                        if (textoA === '-' || textoA === 'Nunca') numA = novaOrdem === 'asc' ? -999999 : 999999;
                        if (textoB === '-' || textoB === 'Nunca') numB = novaOrdem === 'asc' ? -999999 : 999999;
                        
                        resultado = numA - numB;
                    }} else if (tipoColuna === 'data') {{
                        let dataA = parseDataBR(textoA);
                        let dataB = parseDataBR(textoB);
                        
                        resultado = dataA.getTime() - dataB.getTime();
                    }} else {{
                        if (textoA === '-' || textoA === 'Nunca') textoA = novaOrdem === 'asc' ? 'zzz' : '';
                        if (textoB === '-' || textoB === 'Nunca') textoB = novaOrdem === 'asc' ? 'zzz' : '';
                        
                        resultado = textoA.localeCompare(textoB, 'pt-BR', {{ numeric: true }});
                    }}
                    
                    return novaOrdem === 'asc' ? resultado : -resultado;
                }});
                
                linhas.forEach(linha => tbody.appendChild(linha));
                
                // Atualizar ícones de favoritos após reordenação
                atualizarIconesFavoritos();
            }}
            
            // ORDENAÇÃO DA TABELA INDIVIDUAL
            let estadoOrdenacaoIndividual = {{}};
            
            function ordenarTabelaIndividual(indiceColuna, tipoColuna) {{
                const tabela = document.querySelector('#tabelaIndividual table');
                if (!tabela) return;
                
                const tbody = tabela.querySelector('tbody');
                const linhas = Array.from(tbody.querySelectorAll('tr'));
                
                const estadoAtual = estadoOrdenacaoIndividual[indiceColuna] || 'neutro';
                let novaOrdem;
                if (estadoAtual === 'neutro' || estadoAtual === 'desc') {{
                    novaOrdem = 'asc';
                }} else {{
                    novaOrdem = 'desc';
                }}
                estadoOrdenacaoIndividual[indiceColuna] = novaOrdem;
                
                tabela.querySelectorAll('th .sort-indicator').forEach(indicator => {{
                    indicator.className = 'bi bi-arrows-expand sort-indicator';
                }});
                
                const headerAtual = tabela.querySelectorAll('th')[indiceColuna];
                const indicatorAtual = headerAtual.querySelector('.sort-indicator');
                if (indicatorAtual) {{
                    indicatorAtual.className = `bi bi-arrow-${{novaOrdem === 'asc' ? 'up' : 'down'}} sort-indicator active`;
                }}
                
                linhas.sort((linhaA, linhaB) => {{
                    let textoA = linhaA.cells[indiceColuna].textContent.trim();
                    let textoB = linhaB.cells[indiceColuna].textContent.trim();
                    
                    const badgeA = linhaA.cells[indiceColuna].querySelector('.badge');
                    const badgeB = linhaB.cells[indiceColuna].querySelector('.badge');
                    if (badgeA) textoA = badgeA.textContent.trim();
                    if (badgeB) textoB = badgeB.textContent.trim();
                    
                    let resultado = 0;
                    
                    if (tipoColuna === 'numero') {{
                        let numA = parseFloat(textoA.replace(/[^\\d.-]/g, '')) || 0;
                        let numB = parseFloat(textoB.replace(/[^\\d.-]/g, '')) || 0;
                        resultado = numA - numB;
                    }} else if (tipoColuna === 'data') {{
                        let dataA = parseDataBR(textoA);
                        let dataB = parseDataBR(textoB);
                        
                        resultado = dataA.getTime() - dataB.getTime();
                    }} else {{
                        resultado = textoA.localeCompare(textoB, 'pt-BR', {{ numeric: true }});
                    }}
                    
                    return novaOrdem === 'asc' ? resultado : -resultado;
                }});
                
                linhas.forEach(linha => tbody.appendChild(linha));
            }}
            
            // Download Excel - Análise Completa (COM DADOS DAS DIMENSÕES)
            function downloadAnaliseCompleta() {{
                // Obter dados filtrados
                const rows = document.querySelectorAll('#tabelaAnalise tbody tr');
                const dadosVisiveis = [];
                
                rows.forEach(row => {{
                    if (row.style.display !== 'none') {{
                        const parceiroNome = row.cells[0].textContent.trim();
                        const dadoCompleto = todosOsDados.find(item => item.Parceiro === parceiroNome);
                        if (dadoCompleto) {{
                            dadosVisiveis.push(dadoCompleto);
                        }}
                    }}
                }});
                
                const wb = XLSX.utils.book_new();
                const ws = XLSX.utils.json_to_sheet(dadosVisiveis);
                XLSX.utils.book_append_sheet(wb, ws, "Análise Completa");
                XLSX.writeFile(wb, "livelo_analise_completa_{metricas['ultima_atualizacao'].replace('/', '_')}.xlsx");
            }}
            
            // CARREGAR ANÁLISE INDIVIDUAL COM LOGO E NOMES CORRIGIDOS - RESUMO FORA DA TABELA
            function carregarAnaliseIndividual() {{
                const chaveUnica = document.getElementById('parceiroSelect').value;
                if (!chaveUnica) return;
                
                estadoOrdenacaoIndividual = {{}};
                
                const [parceiro, moeda] = chaveUnica.split('|');
                parceiroSelecionado = `${{parceiro}} (${{moeda}})`;
                
                const historicoCompleto = dadosHistoricosCompletos.filter(item => 
                    item.Parceiro === parceiro && item.Moeda === moeda
                );
                
                const dadosResumo = todosOsDados.filter(item => 
                    item.Parceiro === parceiro && item.Moeda === moeda
                );
                
                // Obter logo do parceiro
                const logoUrl = dadosResumo.length > 0 ? dadosResumo[0].Logo_Link : '';
                const logoHtml = logoUrl ? `<img src="${{logoUrl}}" class="logo-parceiro" alt="Logo ${{parceiro}}" onerror="this.style.display='none'">` : '';
                
                document.getElementById('tituloAnaliseIndividual').innerHTML = 
                    `<div class="d-flex align-items-center">${{logoHtml}}<span>Histórico Detalhado - ${{parceiro}} (${{moeda}}) - ${{historicoCompleto.length}} registros</span></div>`;
                
                if (historicoCompleto.length === 0) {{
                    document.getElementById('tabelaIndividual').innerHTML = 
                        '<div class="p-3 text-center text-muted">Nenhum dado encontrado para este parceiro.</div>';
                    return;
                }}
                
                // Montar tabela do histórico (SEM o resumo no final)
                let html = `
                    <table class="table table-hover table-sm">
                        <thead>
                            <tr>
                                <th onclick="ordenarTabelaIndividual(0, 'data')" style="cursor: pointer;">
                                    Data/Hora <i class="bi bi-arrows-expand sort-indicator"></i>
                                </th>
                                <th onclick="ordenarTabelaIndividual(1, 'numero')" style="cursor: pointer;">
                                    Pontos <i class="bi bi-arrows-expand sort-indicator"></i>
                                </th>
                                <th onclick="ordenarTabelaIndividual(2, 'numero')" style="cursor: pointer;">
                                    Valor <i class="bi bi-arrows-expand sort-indicator"></i>
                                </th>
                                <th onclick="ordenarTabelaIndividual(3, 'texto')" style="cursor: pointer;">
                                    Moeda <i class="bi bi-arrows-expand sort-indicator"></i>
                                </th>
                                <th onclick="ordenarTabelaIndividual(4, 'texto')" style="cursor: pointer;">
                                    Oferta <i class="bi bi-arrows-expand sort-indicator"></i>
                                </th>
                                <th onclick="ordenarTabelaIndividual(5, 'numero')" style="cursor: pointer;">
                                    Pontos/Moeda <i class="bi bi-arrows-expand sort-indicator"></i>
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                historicoCompleto.sort((a, b) => new Date(b.Timestamp) - new Date(a.Timestamp));
                
                historicoCompleto.forEach(item => {{
                    const dataFormatada = new Date(item.Timestamp).toLocaleString('pt-BR');
                    const pontosPorMoeda = item.Valor > 0 ? (item.Pontos / item.Valor).toFixed(2) : '0.00';
                    const corOferta = item.Oferta === 'Sim' ? 'success' : 'secondary';
                    const valorFormatado = (item.Valor || 0).toFixed(2).replace('.', ',');
                    
                    html += `
                        <tr>
                            <td style="font-size: 0.75rem;">${{dataFormatada}}</td>
                            <td><strong>${{item.Pontos || 0}}</strong></td>
                            <td>${{item.Moeda}} ${{valorFormatado}}</td>
                            <td><span class="badge bg-info">${{item.Moeda}}</span></td>
                            <td><span class="badge bg-${{corOferta}}">${{item.Oferta}}</span></td>
                            <td><strong>${{pontosPorMoeda}}</strong></td>
                        </tr>
                    `;
                }});
                
                html += '</tbody></table>';
                
                // DEFINIR HTML DA TABELA
                document.getElementById('tabelaIndividual').innerHTML = html;
                
                // RESUMO ESTATÍSTICO SEPARADO - FORA DA TABELA (com contraste corrigido)
                if (dadosResumo.length > 0) {{
                    const resumo = dadosResumo[0];
                    const resumoHtml = `
                        <div class="mt-3 p-3 resumo-estatistico-container">
                            <h6 class="mb-3 resumo-titulo"><i class="bi bi-bar-chart me-2"></i>Resumo Estatístico</h6>
                            <div class="row g-2">
                                <div class="col-md-3 col-6">
                                    <div class="card border-0 bg-white text-center p-2">
                                        <div class="fw-bold text-primary">${{resumo.Categoria_Dimensao}}</div>
                                        <small class="text-muted">Categoria</small>
                                    </div>
                                </div>
                                <div class="col-md-3 col-6">
                                    <div class="card border-0 bg-white text-center p-2">
                                        <div class="fw-bold text-info">Tier ${{resumo.Tier}}</div>
                                        <small class="text-muted">Tier</small>
                                    </div>
                                </div>
                                <div class="col-md-3 col-6">
                                    <div class="card border-0 bg-white text-center p-2">
                                        <div class="fw-bold text-success">${{resumo.Dias_Casa}}</div>
                                        <small class="text-muted">Dias Casa</small>
                                    </div>
                                </div>
                                <div class="col-md-3 col-6">
                                    <div class="card border-0 bg-white text-center p-2">
                                        <div class="fw-bold text-warning">${{resumo.Total_Ofertas_Historicas}}</div>
                                        <small class="text-muted">Total Ofertas</small>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="row g-2 mt-2">
                                <div class="col-md-4">
                                    <div class="card border-0 bg-white text-center p-2">
                                        <div class="fw-bold" style="color: ${{resumo.Variacao_Pontos >= 0 ? '#28a745' : '#dc3545'}}">
                                            ${{resumo.Variacao_Pontos > 0 ? '+' : ''}}${{resumo.Variacao_Pontos.toFixed(1)}}%
                                        </div>
                                        <small class="text-muted">Variação %</small>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="card border-0 bg-white text-center p-2">
                                        <div class="fw-bold text-secondary">${{resumo.Status_Casa}}</div>
                                        <small class="text-muted">Experiência</small>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="card border-0 bg-white text-center p-2">
                                        <div class="fw-bold text-dark">${{resumo.Gasto_Formatado}}</div>
                                        <small class="text-muted">Gasto Atual</small>
                                    </div>
                                </div>
                            </div>
                            
                            ${{resumo.URL_Parceiro ? `
                            <div class="row g-2 mt-2">
                                <div class="col-12">
                                    <div class="card border-0 bg-white text-center p-2">
                                        <a href="${{resumo.URL_Parceiro}}" target="_blank" class="btn btn-outline-primary btn-sm">
                                            <i class="bi bi-box-arrow-up-right me-1"></i>Visitar Página do Parceiro
                                        </a>
                                    </div>
                                </div>
                            </div>
                            ` : ''}}
                        </div>
                    `;
                    
                    // ADICIONAR RESUMO DEPOIS DO CARD DA TABELA (FORA DELE)
                    const cardTabela = document.querySelector('#individual .card:last-child');
                    cardTabela.insertAdjacentHTML('afterend', resumoHtml);
                }}
            }}
            
            // Download Excel - Individual
            function downloadAnaliseIndividual() {{
                const chaveUnica = document.getElementById('parceiroSelect').value;
                if (!chaveUnica) {{
                    alert('Selecione um parceiro primeiro');
                    return;
                }}
                
                const [parceiro, moeda] = chaveUnica.split('|');
                
                const historicoCompleto = dadosHistoricosCompletos.filter(item => 
                    item.Parceiro === parceiro && item.Moeda === moeda
                );
                const dadosResumo = todosOsDados.filter(item => 
                    item.Parceiro === parceiro && item.Moeda === moeda
                );
                
                const wb = XLSX.utils.book_new();
                
                if (historicoCompleto.length > 0) {{
                    const ws1 = XLSX.utils.json_to_sheet(historicoCompleto);
                    XLSX.utils.book_append_sheet(wb, ws1, "Histórico Completo");
                }}
                
                if (dadosResumo.length > 0) {{
                    const ws2 = XLSX.utils.json_to_sheet(dadosResumo);
                    XLSX.utils.book_append_sheet(wb, ws2, "Análise Resumo");
                }}
                
                const nomeArquivo = `livelo_${{parceiro.replace(/[^a-zA-Z0-9]/g, '_')}}_${{moeda}}_completo.xlsx`;
                XLSX.writeFile(wb, nomeArquivo);
            }}
            
            // Download dados RAW (COM DADOS DAS DIMENSÕES)
            function downloadDadosRaw() {{
                const wb = XLSX.utils.book_new();
                const ws = XLSX.utils.json_to_sheet(dadosRawCompletos);
                XLSX.utils.book_append_sheet(wb, ws, "Dados Raw Livelo");
                
                const dataAtual = new Date().toISOString().slice(0, 10).replace(/-/g, '_');
                XLSX.writeFile(wb, `livelo_dados_raw_${{dataAtual}}.xlsx`);
            }}
            
            // Auto-carregar primeiro parceiro quando entrar na aba
            document.querySelector('[data-bs-target="#individual"]').addEventListener('click', function() {{
                setTimeout(() => {{
                    const select = document.getElementById('parceiroSelect');
                    if (select && select.selectedIndex === 0 && select.options.length > 1) {{
                        select.selectedIndex = 1;
                        carregarAnaliseIndividual();
                    }}
                }}, 200);
            }});
            
            // INICIALIZAÇÃO
            document.addEventListener('DOMContentLoaded', function() {{
                initTheme();
                
                // Inicializar notificações Firebase
                setTimeout(initializeNotifications, 1000);
                
                // Verificar se banner foi dispensado
                if (!localStorage.getItem('notification-banner-dismissed')) {{
                    setTimeout(showNotificationBanner, 2000);
                }}
                
                // Inicializar filtros temporais
                setTimeout(inicializarFiltrosTemporal, 1000);
                
                // Inicializar sistema de favoritos
                atualizarCarteira();
                
                // Verificar favoritos com ofertas periodicamente
                setInterval(checkFavoritesWithOffers, 30000); // A cada 30 segundos
                
                // DEBUG: Verificar mudanças detectadas
                console.log('Mudanças detectadas:', {{
                    'ganharam_oferta': {len(mudancas['ganharam_oferta'])},
                    'perderam_oferta': {len(mudancas['perderam_oferta'])},
                    'novos_parceiros': {len(mudancas['novos_parceiros'])},
                    'parceiros_sumidos': {len(mudancas['parceiros_sumidos'])},
                    'grandes_mudancas': {len(mudancas['grandes_mudancas_pontos'])}
                }});
                
                // Configurar event listeners para filtros ATUALIZADOS
                document.getElementById('filtroCategoriaComplex').addEventListener('change', aplicarFiltros);
                document.getElementById('filtroTier').addEventListener('change', aplicarFiltros);
                document.getElementById('filtroOferta').addEventListener('change', aplicarFiltros);
                document.getElementById('filtroExperiencia').addEventListener('change', aplicarFiltros);
                document.getElementById('filtroFrequencia').addEventListener('change', aplicarFiltros);
                
                // Atualizar ícones de favoritos quando trocar de aba
                document.querySelectorAll('[data-bs-toggle="pill"]').forEach(tab => {{
                    tab.addEventListener('shown.bs.tab', function() {{
                        setTimeout(atualizarIconesFavoritos, 100);
                    }});
                }});
                
                setTimeout(() => {{
                    if (document.querySelector('#individual.show.active')) {{
                        const select = document.getElementById('parceiroSelect');
                        if (select && select.options.length > 1) {{
                            select.selectedIndex = 1;
                            carregarAnaliseIndividual();
                        }}
                    }}
                }}, 1000);
            }});
        </script>
        
        {self._gerar_javascript_filtros_temporal()}
    </body>
    </html>
            """
            
        return html
