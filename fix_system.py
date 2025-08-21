#!/usr/bin/env python3
"""
Script de Correção Automática - Livelo Scraper
Identifica e corrige problemas comuns no sistema
"""

import os
import json
import shutil
import subprocess
from datetime import datetime

class LiveloSystemFixer:
    def __init__(self):
        self.problems_found = []
        self.fixes_applied = []
        
    def log(self, message, type="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        if type == "error":
            print(f"❌ [{timestamp}] {message}")
        elif type == "warning":
            print(f"⚠️ [{timestamp}] {message}")
        elif type == "success":
            print(f"✅ [{timestamp}] {message}")
        else:
            print(f"ℹ️ [{timestamp}] {message}")
    
    def check_html_generation(self):
        """Verifica se o HTML está sendo gerado corretamente"""
        self.log("Verificando geração do HTML...")
        
        if not os.path.exists('relatorio_livelo.html'):
            self.problems_found.append("HTML não encontrado")
            self.log("HTML não encontrado - executando reporter...", "warning")
            
            # Tentar executar o reporter
            if os.path.exists('livelo_parceiros.xlsx'):
                try:
                    result = subprocess.run([
                        'python', 'livelo_reporter.py', 'livelo_parceiros.xlsx'
                    ], capture_output=True, text=True, timeout=300)
                    
                    if result.returncode == 0:
                        self.log("Reporter executado com sucesso", "success")
                        self.fixes_applied.append("HTML regenerado")
                    else:
                        self.log(f"Erro no reporter: {result.stderr}", "error")
                except Exception as e:
                    self.log(f"Erro ao executar reporter: {e}", "error")
            else:
                self.log("Arquivo Excel não encontrado para gerar HTML", "error")
                return False
        
        # Verificar tamanho e conteúdo do HTML
        if os.path.exists('relatorio_livelo.html'):
            size = os.path.getsize('relatorio_livelo.html')
            if size < 50000:  # Menos de 50KB indica problema
                self.log(f"HTML muito pequeno: {size:,} bytes", "warning")
                self.problems_found.append(f"HTML pequeno ({size} bytes)")
            else:
                self.log(f"HTML OK: {size:,} bytes", "success")
            
            # Verificar conteúdo
            with open('relatorio_livelo.html', 'r', encoding='utf-8') as f:
                content = f.read()
                if 'Livelo Analytics Pro' not in content:
                    self.log("HTML não contém título esperado", "error")
                    self.problems_found.append("HTML malformado")
                elif 'toggleFavorito' not in content:
                    self.log("Sistema de favoritos ausente no HTML", "warning")
                    self.fix_favorites_system()
                else:
                    self.log("Conteúdo HTML validado", "success")
        
        return True
    
    def fix_favorites_system(self):
        """Corrige o sistema de favoritos no HTML"""
        self.log("Corrigindo sistema de favoritos...")
        
        if not os.path.exists('relatorio_livelo.html'):
            self.log("HTML não encontrado para correção", "error")
            return False
        
        # JavaScript corrigido para favoritos
        favorites_js = '''
<script>
// ========== SISTEMA DE FAVORITOS CORRIGIDO ==========
let favoritosMemoria = []; // Fallback se localStorage não funcionar

function salvarFavoritos(favoritos) {
    try {
        localStorage.setItem('liveloFavoritos', JSON.stringify(favoritos));
        favoritosMemoria = favoritos;
    } catch (e) {
        console.warn('LocalStorage indisponível, usando memória temporária');
        favoritosMemoria = favoritos;
    }
}

function carregarFavoritos() {
    try {
        const favoritos = localStorage.getItem('liveloFavoritos');
        if (favoritos) {
            const parsed = JSON.parse(favoritos);
            favoritosMemoria = parsed;
            return parsed;
        }
    } catch (e) {
        console.warn('Erro ao carregar localStorage');
    }
    return favoritosMemoria;
}

function toggleFavorito(parceiro, moeda) {
    if (!parceiro || !moeda) return;
    
    const chave = `${parceiro}|${moeda}`;
    let favoritos = carregarFavoritos();
    
    const botao = document.querySelector(`button[data-parceiro="${parceiro}"][data-moeda="${moeda}"]`);
    if (!botao) {
        console.warn(`Botão não encontrado para ${parceiro} ${moeda}`);
        return;
    }
    
    const icone = botao.querySelector('i');
    if (!icone) return;
    
    if (favoritos.includes(chave)) {
        favoritos = favoritos.filter(f => f !== chave);
        botao.classList.remove('ativo');
        icone.className = 'bi bi-star';
        botao.title = 'Adicionar aos favoritos';
        console.log(`Removido: ${chave}`);
    } else {
        favoritos.push(chave);
        botao.classList.add('ativo');
        icone.className = 'bi bi-star-fill';
        botao.title = 'Remover dos favoritos';
        console.log(`Adicionado: ${chave}`);
    }
    
    salvarFavoritos(favoritos);
    atualizarMinhaCarteira();
}

function inicializarFavoritos() {
    const favoritos = carregarFavoritos();
    console.log(`Inicializando ${favoritos.length} favoritos`);
    
    favoritos.forEach(chave => {
        const [parceiro, moeda] = chave.split('|');
        const botao = document.querySelector(`button[data-parceiro="${parceiro}"][data-moeda="${moeda}"]`);
        if (botao) {
            botao.classList.add('ativo');
            const icone = botao.querySelector('i');
            if (icone) {
                icone.className = 'bi bi-star-fill';
                botao.title = 'Remover dos favoritos';
            }
        }
    });
    
    atualizarMinhaCarteira();
}

function atualizarMinhaCarteira() {
    const container = document.getElementById('minhaCarteira');
    if (!container) return;
    
    const favoritos = carregarFavoritos();
    
    if (favoritos.length === 0) {
        container.innerHTML = `
            <div class="carteira-vazia">
                <i class="bi bi-star" style="font-size: 3rem; color: #ccc; margin-bottom: 15px;"></i>
                <h6>Sua carteira está vazia</h6>
                <p>Clique na estrela ⭐ ao lado dos parceiros para adicioná-los aqui!</p>
            </div>
        `;
        return;
    }
    
    let html = `<h6 class="mb-3"><i class="bi bi-star-fill me-2"></i>Minha Carteira (${favoritos.length})</h6>`;
    
    favoritos.forEach(chave => {
        const [parceiro, moeda] = chave.split('|');
        const dados = window.dadosAnalise?.find(item => 
            item.Parceiro === parceiro && item.Moeda === moeda
        );
        
        if (dados) {
            const pontos = dados.Pontos_por_Moeda_Atual || 0;
            const temOferta = dados.Tem_Oferta_Hoje;
            const categoria = dados.Categoria_Dimensao || 'N/A';
            
            html += `
                <div class="carteira-item">
                    <div>
                        <div class="carteira-nome">${parceiro} (${moeda})</div>
                        <div class="carteira-info">
                            ${categoria} • ${temOferta ? '🎯 Em oferta' : '⏳ Sem oferta'}
                        </div>
                    </div>
                    <div class="carteira-pontos">
                        ${pontos.toFixed(1)} pts
                    </div>
                </div>
            `;
        }
    });
    
    container.innerHTML = html;
}

// Inicializar quando DOM estiver pronto
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inicializarFavoritos);
} else {
    inicializarFavoritos();
}

// ========== FIM DO SISTEMA DE FAVORITOS ==========
</script>'''
        
        try:
            with open('relatorio_livelo.html', 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Remover JavaScript antigo se existir
            if 'toggleFavorito' in content:
                # Encontrar e substituir o script antigo
                import re
                content = re.sub(r'<script>.*?toggleFavorito.*?</script>', '', content, flags=re.DOTALL)
            
            # Adicionar novo JavaScript antes do </body>
            content = content.replace('</body>', f'{favorites_js}\n</body>')
            
            with open('relatorio_livelo.html', 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.log("Sistema de favoritos corrigido no HTML", "success")
            self.fixes_applied.append("Sistema de favoritos atualizado")
            return True
            
        except Exception as e:
            self.log(f"Erro ao corrigir favoritos: {e}", "error")
            return False
    
    def check_firebase_config(self):
        """Verifica e cria configuração do Firebase"""
        self.log("Verificando configuração Firebase...")
        
        # Verificar firebase.json
        if not os.path.exists('firebase.json'):
            self.log("firebase.json não encontrado - já deve ter sido criado pelo GitHub", "warning")
        else:
            self.log("firebase.json encontrado", "success")
        
        # Verificar diretório public
        if not os.path.exists('public'):
            os.makedirs('public')
            self.log("Diretório public criado", "success")
            self.fixes_applied.append("Diretório public criado")
        
        return True
    
    def prepare_deploy_files(self):
        """Prepara arquivos para deploy"""
        self.log("Preparando arquivos para deploy...")
        
        if not os.path.exists('public'):
            os.makedirs('public')
        
        # Copiar HTML principal
        if os.path.exists('relatorio_livelo.html'):
            shutil.copy2('relatorio_livelo.html', 'public/index.html')
            self.log("HTML copiado para public/index.html", "success")
            self.fixes_applied.append("HTML preparado para deploy")
        
        # Copiar arquivos PWA
        pwa_files = [
            'manifest.json',
            'sw.js', 
            'firebase-config-runtime.js',
            'firebase-config.json'
        ]
        
        for file in pwa_files:
            if os.path.exists(file):
                shutil.copy2(file, f'public/{file}')
                self.log(f"Copiado: {file}", "success")
        
        # Verificar se index.html existe no public
        public_index = 'public/index.html'
        if os.path.exists(public_index):
            size = os.path.getsize(public_index)
            self.log(f"Deploy preparado: index.html ({size:,} bytes)", "success")
            return True
        else:
            self.log("Falha ao preparar deploy - index.html ausente", "error")
            return False
    
    def run_diagnostics(self):
        """Executa diagnóstico completo"""
        print("\n🔍 DIAGNÓSTICO LIVELO SCRAPER")
        print("=" * 50)
        
        self.check_html_generation()
        self.check_firebase_config()
        self.prepare_deploy_files()
        
        print("\n📊 RESUMO")
        print("=" * 50)
        
        if self.problems_found:
            print(f"❌ Problemas encontrados: {len(self.problems_found)}")
            for problem in self.problems_found:
                print(f"   • {problem}")
        
        if self.fixes_applied:
            print(f"✅ Correções aplicadas: {len(self.fixes_applied)}")
            for fix in self.fixes_applied:
                print(f"   • {fix}")
        
        if not self.problems_found:
            print("✅ Sistema parece estar funcionando corretamente!")
        
        print("\n🚀 PRÓXIMOS PASSOS RECOMENDADOS:")
        print("1. Execute: python main.py --apenas-analise")
        print("2. Teste o HTML gerado localmente")
        print("3. Configure tokens FCM reais se quiser notificações")
        print("4. Faça commit e push para testar GitHub Actions")
        print("5. Verifique deploy em https://gcaressato.github.io/livelo_scraper/")
        
        return len(self.problems_found) == 0

def main():
    """Executa correção automática"""
    fixer = LiveloSystemFixer()
    success = fixer.run_diagnostics()
    
    print(f"\n{'✅ DIAGNÓSTICO CONCLUÍDO COM SUCESSO' if success else '⚠️ DIAGNÓSTICO CONCLUÍDO COM PROBLEMAS'}")
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())