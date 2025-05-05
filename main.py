import subprocess
import sys
import os
import time

def run_script(script_name):
    """Executa um script Python e retorna True se bem-sucedido, False caso contrário."""
    print(f"Executando {script_name}...")
    result = subprocess.run([sys.executable, script_name], capture_output=True, text=True)
    
    # Imprime a saída
    print(f"Saída de {script_name}:")
    print(result.stdout)
    
    if result.stderr:
        print(f"Erros de {script_name}:")
        print(result.stderr)
    
    # Retorna True se o script saiu com código de status zero
    return result.returncode == 0

def main():
    """Função principal para executar os scripts de scraper e reporter."""
    # Executa o scraper
    scraper_success = run_script("livelo_scraper.py")
    
    if not scraper_success:
        print("Falha no scraper. Saindo.")
        sys.exit(1)
    
    # Espera um pouco para garantir que as operações de arquivo sejam concluídas
    time.sleep(2)
    
    # Executa o reporter
    reporter_success = run_script("livelo_reporter.py")
    
    if not reporter_success:
        print("Falha no reporter. Saindo.")
        sys.exit(1)
    
    print("Todos os scripts foram executados com sucesso.")

if __name__ == "__main__":
    main()
