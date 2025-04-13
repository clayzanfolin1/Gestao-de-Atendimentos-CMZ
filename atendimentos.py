import os
import json
import zipfile
import copy
from datetime import datetime, date, time, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
import platform
import locale
import hashlib
from tkinter import Toplevel, Menu
import traceback
import sys
import io

# Verifica se sys.stdout e sys.stderr não são None antes de reconfigurar
if sys.stdout is not None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr is not None:
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Configura o locale para UTF-8
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        # Tenta configurar o locale para Portuguese_Brazil (Windows)
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.UTF-8')
    except locale.Error:
        # Usa o locale padrão do sistema se pt_BR não estiver disponível
        locale.setlocale(locale.LC_ALL, '')

# Verifica o encoding atual
print(f"Encoding do stdout: {sys.stdout.encoding if sys.stdout else 'None'}")
print(f"Encoding do stderr: {sys.stderr.encoding if sys.stderr else 'None'}")
print(f"Encoding do locale: {locale.getpreferredencoding()}")

def mostrar_erro(janela_pai, mensagem):
    """
    Exibe uma caixa de erro que fica sempre no topo da janela pai.
    """
    # Cria uma janela temporária como filha da janela pai
    temp_window = Toplevel(janela_pai)
    temp_window.withdraw()  # Esconde a janela temporária
    temp_window.wm_attributes("-topmost", 1)  # Define a janela como sempre no topo
    messagebox.showerror("Erro", mensagem, parent=temp_window)  # Exibe a caixa de erro
    temp_window.destroy()  # Fecha a janela temporária
    # Usar  mostrar_erro(window, f"Menssagem: {str(e)}")

def mostrar_sucesso(janela_pai, mensagem):
    """
    Exibe uma caixa de sucesso que fica sempre no topo da janela pai.
    """
    # Cria uma janela temporária como filha da janela pai
    temp_window = Toplevel(janela_pai)
    temp_window.withdraw()  # Esconde a janela temporária
    temp_window.wm_attributes("-topmost", 1)  # Define a janela como sempre no topo
    messagebox.showinfo("Sucesso", mensagem, parent=temp_window)  # Exibe a caixa de sucesso
    temp_window.destroy()  # Fecha a janela temporária
    #usar: mostrar_sucesso(window, "mesagem")

def corrigir_ortografia(texto):
    spell = SpellChecker(language='pt')  # Define o idioma para português
    palavras = texto.split()
    palavras_corrigidas = [spell.correction(palavra) for palavra in palavras]
    return ' '.join(palavras_corrigidas)


# Função para configurar o locale para português do Brasil
def configurar_locale_pt_br():
    try:
        # Tenta configurar o locale para pt_BR.UTF-8 (Linux/macOS)
        locale.setlocale(locale.LC_TIME, "pt_BR.UTF-8")
    except locale.Error:
        try:
            # Tenta configurar o locale para Portuguese_Brazil (Windows)
            locale.setlocale(locale.LC_TIME, "Portuguese_Brazil")
        except locale.Error:
            # Caso o locale pt_BR não esteja disponível, usa o locale padrão do sistema
            locale.setlocale(locale.LC_TIME, "")
            print(
                "Aviso: Locale pt_BR não está disponível. Usando o locale padrão do sistema."
            )


# Configura o locale para português do Brasil
configurar_locale_pt_br()

ESTADOS = {0: "inicio", 1: "em_andamento", 2: "pausado", 3: "retomado", 4: "finalizado"}


class AtendimentoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestão de Atendimentos CMZ")
        # Salva as configurações ao fechar a janela
        self.root.protocol("WM_DELETE_WINDOW", self.ao_fechar_janela)
        #self.root.geometry("1200x800")

        # Configuração adicional para estilização no Linux
        if platform.system() == "Linux":
            self.configurar_estilo_menu_linux()

        # Ajusta o tamanho e a posição da janela
        self.ajustar_tamanho_posicao_janela()

        # Mantém a janela acima da barra de tarefas
        #self.root.wm_attributes("-topmost", 1)

        # Flag para controlar o carregamento inicial
        self.carregamento_inicial = True

        # Define a pasta base de acordo com o sistema operacional
        if platform.system() == "Linux":
            # No Linux/macOS, usa a pasta home com um ponto no início
            self.base_dir = Path.home() / ".cmz-atendimentos" #CMZ

        else:
            # No Windows, usa a pasta AppData\Local
            self.base_dir = Path.home() / "AppData" / "Local" / "cmz-atendimentos"

        # Cria a pasta de atendimentos (que conterá os anos)
        self.atendimentos_dir = self.base_dir / "atendimentos"
        self.atendimentos_dir.mkdir(parents=True, exist_ok=True)


        # Cria a pasta de dados do usuário
        self.dados_usuario_dir = self.base_dir / "dados do usuario"
        self.dados_usuario_dir.mkdir(parents=True, exist_ok=True)

        # Cria a pasta de usuários
        self.usuarios_dir = self.base_dir / "usuarios"
        self.usuarios_dir.mkdir(parents=True, exist_ok=True)

        # Cria a pasta de configurações
        self.config_dir = self.base_dir / "configuracoes"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Cria a pasta de backups
        self.backup_dir = self.base_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Carrega as configurações da janela
        self.carregar_configuracoes_janela()

        # Carrega as configurações das colunas do histórico
        self.carregar_configuracoes_colunas()

        # Configura o locale para português do Brasil
        configurar_locale_pt_br()

        # Cria a pasta se ela não existir
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Ordena os arquivos ao iniciar
        self.ordenar_arquivos_alfabeticamente()

        # Verifica/carrega o número do operador
        self.verificar_operador()

        # Criação do menu superior
        self.criar_menu_superior()

        # Variável para controlar o estado da hora automática
        self.hora_automatica = True

        # Inicia a atualização automática da hora
        self.atualizar_hora()

        # Cria as pastas do ano e do mês corrente, se não existirem
        self.criar_pasta_ano_mes_corrente()

        # Configurar o redimensionamento responsivo
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # Referência à janela de anotações
        self.janela_anotacoes = None

        # Referência à janela de espelhamentos
        self.janela_espelhamentos = None


        self.estado_atual = ESTADOS[0]
        self.eventos = []
        self.atendimentos_abertos = []
        self.historico = []
        self.clientes = []
        self.cliente_var = tk.StringVar()
        self.usuario_var = tk.StringVar()
        self.current_historico = []
        self.current_atendimento = None
        self.tmp_atendimentos = {}
        self.after_id = None

        self.carregar_clientes()
        self.carregar_atendimentos_abertos()
        self.carregar_tmp_atendimentos()
        self.limpar_atendimentos_invalidos()

        # Definir colunas do histórico ANTES de criar os widgets
        self.colunas = [
            ("Cliente", 220, 220, True),    # Nome, largura inicial, largura mínima, redimensionável
            ("Data", 80, 80, False),       # Coluna Data fixa
            ("Problema", 220, 220, True),
            ("Tarefa", 170, 170, True),
            ("Tempo", 80, 80, False),      # Coluna Tempo fixa
        ]


        self.criar_widgets_principais()
        self.criar_backup()

        # Configura atalhos para a janela principal
        self.configurar_atalhos_janela(
            self.root,
            [
                self.problema_entry,
                self.tarefa_entry,
                self.dados_usuario_text
            ]
        )

        # Armazena o último item selecionado
        self.last_selected_historico = None
        self.last_selected_item = None
        self.historico_needs_reselection = False  # Flag para controle

        # Atualiza a navegação temporal e carrega o histórico do mês atual
        self.atualizar_navegacao_temporal()
        self.carregar_historico()
        # Agenda a desativação da flag após 2 segundos
        self.root.after(1000, self.desativar_carregamento_inicial)  # 1000 ms = 2 segundos

    def criar_menu_contexto_generico(self, event, janela_pai):
        """
        Menu de contexto genérico que pode ser usado em qualquer janela
        - janela_pai: a janela onde o menu será exibido (self.root, self.janela_anotacoes, etc.)
        """
        # Fecha menu anterior se existir
        if hasattr(self, '_context_menu') and hasattr(self._context_menu, 'winfo_exists') and self._context_menu.winfo_exists():
            self._context_menu.unpost()

        # Cria novo menu
        self._context_menu = Menu(janela_pai, tearoff=0)

        # Função para fechar o menu de forma segura
        def fechar_menu():
            if hasattr(self, '_context_menu') and hasattr(self._context_menu, 'winfo_exists') and self._context_menu.winfo_exists():
                self._context_menu.unpost()
                # Remove o binding de clique fora do menu
                if hasattr(self, '_context_menu_bind_id'):
                    janela_pai.unbind("<Button-1>", self._context_menu_bind_id)
                    del self._context_menu_bind_id

        # Adiciona itens com execução antes de fechar
        itens = [
            ("Selecionar Tudo", lambda: event.widget.tag_add(tk.SEL, "1.0", tk.END)),
            ("Copiar", lambda: event.widget.event_generate("<<Copy>>")),
            ("Recortar", lambda: event.widget.event_generate("<<Cut>>")),
            ("Colar", lambda: event.widget.event_generate("<<Paste>>"))
        ]

        for texto, comando in itens:
            self._context_menu.add_command(
                label=texto,
                command=lambda c=comando: [c(), fechar_menu()]
            )

        # Exibe o menu
        self._context_menu.post(event.x_root, event.y_root)

        # Verifica clique fora do menu
        def verificar_clique_fora(e):
            # Obtém widget clicado
            widget_clicado = e.widget

            # Se não for o menu nem seus itens
            if not (widget_clicado == self._context_menu or
                    any(widget_clicado == item for item in self._context_menu.children.values())):
                fechar_menu()

        # Configura bind apenas para o botão esquerdo
        self._context_menu_bind_id = janela_pai.bind("<Button-1>", verificar_clique_fora, add="+")

        # Remove bind quando menu é fechado
        self._context_menu.bind("<Unmap>", lambda e: fechar_menu())

    def criar_menu_contexto(self, event):
        """Menu de contexto para a janela principal"""
        self.criar_menu_contexto_generico(event, self.root)

    def criar_menu_contexto_anotacoes(self, event):
        """Menu de contexto para a janela de anotações"""
        if hasattr(self, 'janela_anotacoes') and self.janela_anotacoes.winfo_exists():
            self.criar_menu_contexto_generico(event, self.janela_anotacoes)

    def _setup_menu_autoclose(self):
        """Configura os eventos para fechar o menu automaticamente"""
        def close_menu(e=None):
            if hasattr(self, '_context_menu') and self._context_menu.winfo_exists():
                self._context_menu.unpost()

        # Fecha ao clicar em qualquer lugar (usando eventos de baixo nível)
        self.root.bind_all("<Button>", lambda e: close_menu(), add="+")

        # Fecha ao pressionar Esc
        self.root.bind_all("<Escape>", close_menu, add="+")

        # Fecha quando o menu perde foco
        self._context_menu.bind("<Unmap>", lambda e: self._cleanup_menu_bindings())

    def _cleanup_menu_bindings(self):
        """Remove os bindings de fechamento automático"""
        if hasattr(self, '_context_menu'):
            self.root.unbind_all("<Button>")
            self.root.unbind_all("<Escape>")


    def selecionar_tudo(self, event):
        """
        Seleciona todo o texto no widget ScrolledText.
        """
        event.widget.tag_add(tk.SEL, "1.0", tk.END)
        event.widget.mark_set(tk.INSERT, "1.0")
        event.widget.see(tk.INSERT)
        return 'break'  # Impede a propagação do evento

    def adicionar_funcionalidades_texto(self, widget):
        """
        Adiciona as funcionalidades de selecionar tudo e menu de contexto ao widget.
        """
        # Adiciona o evento de teclado para selecionar tudo (Ctrl+A)
        widget.bind("<Control-a>", self.selecionar_tudo)
        widget.bind("<Control-A>", self.selecionar_tudo)  # Para o caso de Caps Lock estar ativado

        # Adiciona o menu de contexto com botão direito do mouse
        widget.bind("<Button-3>", self.criar_menu_contexto)


    def criar_pasta_ano_mes_corrente(self):
        """
        Cria as pastas do ano e do mês corrente, se elas não existirem.
        """
        # Obtém o ano e o mês atuais
        ano_atual = str(datetime.now().year)
        mes_atual = datetime.now().strftime("%B").lower()  # Nome do mês em minúsculas

        # Cria o diretório do ano e do mês dentro da pasta atendimentos
        mes_dir = self.atendimentos_dir / ano_atual / mes_atual
        mes_dir.mkdir(parents=True, exist_ok=True)  # Cria as pastas automaticamente

        # Cria o arquivo todos.txt, se não existir
        todos_path = mes_dir / "todos.txt"
        if not todos_path.exists():
            with open(todos_path, "w", encoding="utf-8") as f:
                f.write("")  # Cria um arquivo vazio

    def alternar_hora_automatica(self):
        self.hora_automatica = not self.hora_automatica

        if self.hora_automatica:
            self.botao_hora_automatica.config(
                text="Desligar Hora Automática",
                foreground="black"  # Cor padrão do texto
            )
            # Reativa a atualização automática da hora
            self.atualizar_hora()
        else:
            self.botao_hora_automatica.config(
                text="Ligar Hora Automática",
                foreground="red"  # Cor vermelha para o texto
            )
            # Desativa a atualização automática da hora
            if self.after_id is not None:
                self.root.after_cancel(self.after_id)
                self.after_id = None

    def atualizar_hora(self):
        """
        Atualiza os campos de hora com a hora atual do sistema.
        """
        hora_atual = datetime.now().strftime("%H:%M")

        # Atualiza os campos de hora no "Atendimento Atual"
        if hasattr(self, "hora_inicio") and self.hora_inicio.winfo_exists():
            self.hora_inicio.delete(0, tk.END)
            self.hora_inicio.insert(0, hora_atual)

        if hasattr(self, "hora_acao") and self.hora_acao.winfo_exists():
            self.hora_acao.delete(0, tk.END)
            self.hora_acao.insert(0, hora_atual)

        if hasattr(self, "hora_pausa") and self.hora_pausa.winfo_exists():
            self.hora_pausa.delete(0, tk.END)
            self.hora_pausa.insert(0, hora_atual)

        if hasattr(self, "hora_fim") and self.hora_fim.winfo_exists():
            self.hora_fim.delete(0, tk.END)
            self.hora_fim.insert(0, hora_atual)

        # Agenda a próxima atualização após 1 segundo (1000 ms)
        if self.hora_automatica:
            self.after_id = self.root.after(1000, self.atualizar_hora)

    def criar_menu_superior(self):
        menubar = tk.Menu(self.root)

        # Itens do menu normais
        menubar.add_command(label="Diretório", command=self.abrir_diretorio)
        menubar.add_command(label="Espelhamentos", command=self.criar_janela_espelhamentos)
        menubar.add_command(label="Anotações", command=self.criar_janela_anotacoes)
        menubar.add_command(label="Alterar Operador", command=self.alterar_operador)
        menubar.add_command(label="Sobre", command=self.mostrar_sobre)

        self.root.config(menu=menubar)

        # Barra de ferramentas com o operador destacado
        toolbar = tk.Frame(self.root, bg='lightgray')
        toolbar.pack(side=tk.TOP, fill=tk.X)

        # Botão da hora automática
        self.botao_hora_automatica = tk.Button(
            toolbar,
            text="Desligar Hora Automática",
            command=self.alternar_hora_automatica,
            foreground="black",
            bg='lightgray'
        )
        self.botao_hora_automatica.pack(side=tk.LEFT, padx=5, pady=2)

        # Botão de atendimento presencial
        self.botao_atendimento_presencial = tk.Button(
            toolbar,
            text="Atendimento Presencial",
            command=self.alternar_atendimento_presencial,
            foreground="black",
            bg='lightgray'
        )
        self.botao_atendimento_presencial.pack(side=tk.LEFT, padx=5, pady=2)

        # Label do operador (estilizado)
        self.operador_label = tk.Label(
            toolbar,
            text=f"Operador: {getattr(self, 'numero_operador', 'Não definido')}",
            fg='green',
            bg='lightgray',
            font=('Helvetica', 10, 'bold'),
            padx=10
        )
        self.operador_label.pack(side=tk.RIGHT)

    def atualizar_operador_label(self):
        """Atualiza o label do operador na toolbar"""
        if hasattr(self, 'operador_label'):
            self.operador_label.config(text=f"Operador: {self.numero_operador}")

    def abrir_diretorio(self):
        """
        Abre o gerenciador de arquivos do sistema na pasta ".cmz-atendimentos".
        """
        if os.name == "nt":  # Windows
            os.startfile(self.base_dir)
        elif os.name == "posix":  # Linux ou macOS
            os.system(f'xdg-open "{self.base_dir}"')
        else:
            messagebox.showerror("Erro", "Sistema operacional não suportado.")

    def obter_proximo_numero_atendimento(self):
        """Obtém o próximo número de atendimento e atualiza o contador"""
        contador_path = self.config_dir / "contador_atendimentos.txt"

        try:
            if contador_path.exists():
                with open(contador_path, "r", encoding="utf-8") as f:
                    numero = int(f.read().strip())
            else:
                numero = 1  # Começa do 1 se o arquivo não existir
        except (ValueError, FileNotFoundError):
            numero = 1  # Se houver erro, começa do 1

        # Salva o próximo número para uso futuro
        with open(contador_path, "w", encoding="utf-8") as f:
            f.write(str(numero + 1))

        return f"{self.numero_operador} - {numero:02d}"  # Formato: "operador - numero"

    def mostrar_sobre(self):
        """
        Exibe uma caixa de mensagem com informações sobre o desenvolvedor, licença e versão do software.
        """
        sobre_texto = (
            "Desenvolvedor: Clayton Magalhães Zanfolin   \n\n" "Direitos de uso: Licença Pública Geral GNU versão 2.0   \n\n" "Versão: 1.8   "
        )
        messagebox.showinfo("Sobre", sobre_texto)

    def alternar_atendimento_presencial(self):
        # Alterna o estado do atendimento presencial
        if not hasattr(self, 'atendimento_presencial'):
            self.atendimento_presencial = False

        self.atendimento_presencial = not self.atendimento_presencial

        if self.atendimento_presencial:
            # Ativa o modo presencial
            self.botao_atendimento_presencial.config(foreground="red")
            # Desativa a hora automática
            if self.hora_automatica:
                self.alternar_hora_automatica()
        else:
            # Desativa o modo presencial
            self.botao_atendimento_presencial.config(foreground="black")
            # Ativa a hora automática se estiver desligada
            if not self.hora_automatica:
                self.alternar_hora_automatica()

    def carregar_clientes(self):
        clientes_file = self.base_dir / "clientes.txt"
        try:
            with open(clientes_file, "r", encoding="utf-8") as f:
                self.clientes = [line.strip() for line in f.readlines()]
        except FileNotFoundError:
            self.clientes = []

    def carregar_atendimentos_abertos(self):
        tmp_file = self.base_dir / "tmp.txt"
        try:
            with open(tmp_file, "r", encoding="utf-8") as f:
                dados = json.load(f)
                for atendimento in dados:
                    for evento in atendimento["eventos"]:
                        evento["data"] = datetime.fromisoformat(evento["data"]).date()
                        evento["hora"] = datetime.strptime(
                            evento["hora"], "%H:%M"
                        ).time()
                    self.atendimentos_abertos.append(atendimento)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def carregar_tmp_atendimentos(self):
        tmp_file = self.base_dir / "tmp_atendimentos.txt"
        try:
            with open(tmp_file, "r", encoding="utf-8") as f:
                tmp_serializado = json.load(f)
                self.tmp_atendimentos = {}
                for chave_composta, dados in tmp_serializado.items():
                    # Verifica se o cliente e o usuário não estão vazios
                    if dados.get("cliente", "").strip() and dados.get("usuario", "").strip():
                        eventos = []
                        for evento in dados["eventos"]:
                            data = datetime.strptime(evento["data"], "%Y-%m-%d").date()
                            hora = datetime.strptime(evento["hora"], "%H:%M").time()
                            eventos.append(
                                {"tipo": evento["tipo"], "data": data, "hora": hora}
                            )
                        self.tmp_atendimentos[chave_composta] = {
                            "cliente": dados["cliente"],
                            "usuario": dados.get("usuario", ""),
                            "problema": dados["problema"],
                            "tarefa": dados["tarefa"],
                            "estado": dados["estado"],
                            "eventos": eventos,
                        }
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.tmp_atendimentos = {}

    def salvar_tmp_atendimentos(self):
        tmp_file = self.base_dir / "tmp_atendimentos.txt"
        tmp_serializado = {}
        for chave_composta, dados in self.tmp_atendimentos.items():
            tmp_serializado[chave_composta] = {
                "cliente": dados["cliente"],
                "usuario": dados["usuario"],
                "problema": dados["problema"],
                "tarefa": dados["tarefa"],
                "estado": dados["estado"],
                "eventos": [
                    {
                        "tipo": evento["tipo"],
                        "data": evento["data"].strftime("%Y-%m-%d"),
                        "hora": evento["hora"].strftime("%H:%M"),
                    }
                    for evento in dados["eventos"]
                ],
            }
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(tmp_serializado, f, indent=2, ensure_ascii=False)

    def criar_widgets_principais(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Painel Esquerdo
        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        # Seções principais
        self.criar_secao_clientes(left_panel)
        self.criar_secao_atendimento(left_panel)
        self.criar_secao_abertos(left_panel)
        self.criar_secao_dados_usuario(left_panel)


        # Painel Direito (mantido igual)
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        self.criar_secao_historico(right_panel)

        widgets_texto = [
            self.problema_entry,
            self.tarefa_entry,
            self.dados_usuario_text,
        ]

        for widget in widgets_texto:
            widget.bind("<<Paste>>", self.colar_texto_com_substituicao)

        # Adiciona bind para capturar seleções no treeview
        self.tree.bind('<<TreeviewSelect>>', self.salvar_selecao_atual)

        # Carrega a seleção salva
        self.carregar_ultima_selecao()

    def criar_secao_dados_usuario(self, parent):
        frame = ttk.LabelFrame(parent, text="Dados do Usuário")
        frame.pack(fill=tk.X, pady=5, expand=False)

        self.dados_usuario_text = scrolledtext.ScrolledText(frame, height=10, width=40)
        self.dados_usuario_text.pack(fill=tk.X, padx=5, pady=5)

        # Adiciona as funcionalidades de selecionar tudo e menu de contexto
        self.adicionar_funcionalidades_texto(self.dados_usuario_text)  # Usar self para chamar o método

        # Vincular modificação de texto para salvar
        self.dados_usuario_text.bind("<KeyRelease>", self.salvar_dados_usuario)

    def carregar_operador(self):
        """Carrega o número do operador do arquivo"""
        operador_path = self.config_dir / "operador.txt"
        try:
            if operador_path.exists():
                with open(operador_path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            return None
        except Exception:
            return None

    def solicitar_operador(self):
        """Solicita ao usuário que informe seu número de operador"""
        while True:
            operador = simpledialog.askstring("Operador",
                                            "Informe seu dado de operador:",
                                            parent=self.root)
            if operador and operador.strip():
                operador_path = self.config_dir / "operador.txt"
                with open(operador_path, "w", encoding="utf-8") as f:
                    f.write(operador.strip())
                return operador.strip()
            else:
                messagebox.showwarning("Operador inválido", "O campo do operador não pode ser vazio!")

    def atualizar_display_operador(self):
        """Atualiza o display do operador no menu superior"""
        if hasattr(self, 'numero_operador'):
            # Obtém o menu atual
            menubar = self.root.config('menu')

            # Se o menu existir, atualiza o item do operador
            if menubar:
                # Obtém todos os itens do menu
                menu_items = menubar.children

                # Procura pelo item do operador (que está desabilitado)
                for item in menu_items.values():
                    if isinstance(item, tk.Menu) and item.entrycget(0, 'state') == 'disabled':
                        item.entryconfig(0, label=f"Operador: {self.numero_operador}")
                        break

    def alterar_operador(self):
        novo_operador = simpledialog.askstring("Alterar Operador",
                                            "Informe o novo dado de operador:",
                                            parent=self.root)
        if novo_operador and novo_operador.strip():
            operador_path = self.config_dir / "operador.txt"
            with open(operador_path, "w", encoding="utf-8") as f:
                f.write(novo_operador.strip())
            self.numero_operador = novo_operador.strip()
            self.atualizar_operador_label()  # Atualiza o label
            mostrar_sucesso(self.root, "Operador atualizado com sucesso!")

    def atualizar_menu_operador(self):
        """Atualiza o display do operador no menu"""
        menubar = self.root.config('menu')
        if menubar:
            # Encontra o item do operador (que está na posição 4, considerando os itens anteriores)
            try:
                menubar.entryconfig(4, label=f"Operador: {self.numero_operador}")
            except:
                # Se a posição mudou, faz uma busca pelo item desabilitado
                for i in range(menubar.index('end') + 1):
                    if menubar.entrycget(i, 'state') == 'disabled':
                        menubar.entryconfig(i, label=f"Operador: {self.numero_operador}")
                        break

    def verificar_operador(self):
        """Verifica e carrega o número do operador"""
        operador = self.carregar_operador()
        if not operador:
            operador = self.solicitar_operador()
        # Garante que temos um operador válido
        self.numero_operador = operador if operador else "Não definido"

    def salvar_dados_usuario(self, event=None):
        cliente = self.cliente_var.get().strip()
        usuario = self.usuario_var.get().strip()
        if cliente and usuario:
            filename = f"{cliente}-{usuario}.txt".replace("/", "_")  # Sanitize filename
            file_path = self.dados_usuario_dir / filename
            content = self.dados_usuario_text.get("1.0", tk.END).strip()

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

    def criar_secao_abertos(self, parent):
        frame = ttk.LabelFrame(parent, text="Atendimentos Abertos")
        frame.pack(fill=tk.X, pady=5)

        self.lista_abertos = tk.Listbox(frame, width=30, height=5)
        self.lista_abertos.pack(padx=5, pady=5, fill=tk.X)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=5)

        ttk.Button(btn_frame, text="Retomar", command=self.retomar_atendimento).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(
            btn_frame,
            text="Finalizar sem Concluir",
            command=self.finalizar_sem_concluir,
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            btn_frame, text="Atualizar", command=self.recarregar_lista_abertos
        ).pack(side=tk.LEFT, padx=2)

        self.atualizar_lista_abertos()

    def recarregar_lista_abertos(self):
        self.carregar_tmp_atendimentos()
        self.atualizar_lista_abertos()

    def atualizar_lista_abertos(self):
        self.lista_abertos.delete(0, tk.END)
        for chave_composta in self.tmp_atendimentos:
            self.lista_abertos.insert(tk.END, chave_composta)

    def retomar_atendimento(self):
        selecionado = self.lista_abertos.curselection()
        if not selecionado:
            return

        chave_composta = self.lista_abertos.get(selecionado[0])
        if chave_composta in self.tmp_atendimentos:
            atendimento = self.tmp_atendimentos[chave_composta]

            # Verifica se há um evento de início
            tem_inicio = any(e["tipo"] == "inicio" for e in atendimento["eventos"])

            if not tem_inicio:
                # Se não tem início, pergunta se deseja iniciar
                resposta = messagebox.askyesno(
                    "Atendimento não iniciado",
                    "Este atendimento não foi iniciado. Deseja iniciá-lo agora?",
                    parent=self.root
                )

                if resposta:
                    # Configura os dados do atendimento (igual ao "Iniciar Cliente")
                    self.cliente_var.set(atendimento["cliente"])
                    self.usuario_var.set(atendimento["usuario"])
                    self.problema_entry.delete("1.0", tk.END)
                    self.problema_entry.insert(tk.END, atendimento["problema"])
                    self.tarefa_entry.delete("1.0", tk.END)
                    self.tarefa_entry.insert(tk.END, atendimento["tarefa"])

                    # Carrega os dados do usuário se existirem
                    cliente = atendimento["cliente"].strip()
                    usuario = atendimento["usuario"].strip()
                    if cliente and usuario:
                        filename = f"{cliente}-{usuario}.txt".replace("/", "_")
                        file_path = self.dados_usuario_dir / filename
                        self.dados_usuario_text.delete("1.0", tk.END)
                        if file_path.exists():
                            with open(file_path, "r", encoding="utf-8") as f:
                                self.dados_usuario_text.insert(tk.END, f.read())

                    # Inicia um novo atendimento (igual ao "Iniciar Cliente")
                    self.iniciar_novo_atendimento()

                    # Atualiza a interface para mostrar os campos de início
                    self.estado_atual = ESTADOS[0]  # "inicio"
                    self.atualizar_interface_atendimento()

                    # Mantém no tmp_atendimentos (já está lá)
                    return
                else:
                    return  # Usuário cancelou

            # Se já tem início, procede com a retomada normal
            self.salvar_atendimento_temporario()
            self.carregar_atendimento_temporario(chave_composta)
            self.atualizar_lista_abertos()

            # Carrega dados do usuário
            cliente = atendimento["cliente"].strip()
            usuario = atendimento["usuario"].strip()
            if cliente and usuario:
                filename = f"{cliente}-{usuario}.txt".replace("/", "_")
                file_path = self.dados_usuario_dir / filename
                self.dados_usuario_text.delete("1.0", tk.END)
                if file_path.exists():
                    with open(file_path, "r", encoding="utf-8") as f:
                        self.dados_usuario_text.insert(tk.END, f.read())

    def finalizar_sem_concluir(self):
        selecionado = self.lista_abertos.curselection()
        if not selecionado:
            return

        chave_composta = self.lista_abertos.get(selecionado[0])
        if messagebox.askyesno(
            "Confirmar",
            "O Atendimento será finalizado sem concluir, tem certeza disso?",
        ):
            atendimento = self.tmp_atendimentos.pop(chave_composta, None)
            if atendimento:
                data = datetime.now().date()

                # Cria o caminho dentro da pasta atendimentos/ano/mês
                ano_dir = self.atendimentos_dir / str(data.year)
                mes_dir = ano_dir / data.strftime("%B").lower()
                mes_dir.mkdir(parents=True, exist_ok=True)

                desistente_path = mes_dir / "desistente.txt"
                with open(desistente_path, "a", encoding="utf-8") as f:
                    f.write(
                        f"Cliente: {atendimento['cliente']}\n"
                        f"Usuário: {atendimento['usuario']}\n"
                        f"Problema: {atendimento['problema']}\n"
                        f"Tarefa: {atendimento['tarefa']}\n"
                        f"Data: {data.strftime('%d/%m/%Y')}\n"
                        f"Tempo: 00:00\n"
                        "----------------------------------\n"
                    )

                self.salvar_tmp_atendimentos()
                self.atualizar_lista_abertos()

    def salvar_atendimento_temporario(self):
        if self.current_atendimento and not self.current_atendimento["finalizado"]:
            cliente = self.current_atendimento["cliente"].strip()
            usuario = self.current_atendimento["usuario"].strip()
            # Verifica se o cliente e o usuário não estão vazios
            if cliente and usuario:
                chave_composta = f"{cliente} – {usuario}"
                self.tmp_atendimentos[chave_composta] = {
                    "cliente": cliente,
                    "usuario": usuario,
                    "problema": self.problema_entry.get("1.0", tk.END).strip(),
                    "tarefa": self.tarefa_entry.get("1.0", tk.END).strip(),
                    "eventos": self.eventos,
                    "estado": self.estado_atual,
                }
                self.salvar_tmp_atendimentos()

    def limpar_atendimentos_invalidos(self):
        chaves_invalidas = []
        for chave_composta, dados in self.tmp_atendimentos.items():
            if not dados.get("cliente", "").strip() or not dados.get("usuario", "").strip():
                chaves_invalidas.append(chave_composta)

        for chave in chaves_invalidas:
            del self.tmp_atendimentos[chave]

        if chaves_invalidas:
            self.salvar_tmp_atendimentos()

    def carregar_atendimento_temporario(self, chave_composta):
        if chave_composta in self.tmp_atendimentos:
            dados = self.tmp_atendimentos[chave_composta]
            self.current_atendimento = {
                "cliente": dados["cliente"],
                "usuario": dados.get("usuario", ""),
                "problema": dados["problema"],
                "tarefa": dados["tarefa"],
                "eventos": dados["eventos"],
                "finalizado": False,
            }
            self.eventos = dados["eventos"]

            # Verifica se há um evento de início
            tem_inicio = any(e["tipo"] == "inicio" for e in self.eventos)

            if tem_inicio:
                # Se tem início, verifica o último evento para determinar o estado
                if self.eventos and self.eventos[-1]["tipo"] == "pausa":
                    self.estado_atual = ESTADOS[2]  # "pausado"
                else:
                    self.estado_atual = ESTADOS[1]  # "em_andamento"
            else:
                # Se não tem início, estado deve ser "inicio"
                self.estado_atual = ESTADOS[0]  # "inicio"

            self.cliente_var.set(dados["cliente"])
            self.usuario_var.set(dados["usuario"])
            self.problema_entry.delete("1.0", tk.END)
            self.problema_entry.insert(tk.END, dados["problema"])
            self.tarefa_entry.delete("1.0", tk.END)
            self.tarefa_entry.insert(tk.END, dados["tarefa"])

            self.atualizar_interface_atendimento()

    def criar_secao_clientes(self, parent):
        frame = ttk.LabelFrame(parent, text="Clientes")
        frame.pack(fill=tk.X, pady=5)

        self.cliente_var = tk.StringVar()
        ttk.Label(frame, text="Cliente:").grid(row=0, column=0, sticky=tk.W)
        self.cliente_combobox = ttk.Combobox(
            frame, textvariable=self.cliente_var, values=self.clientes
        )
        self.cliente_combobox.grid(row=0, column=1, padx=5, pady=2)
        self.cliente_combobox.bind("<<ComboboxSelected>>", self.atualizar_usuarios_combobox)

        self.usuario_var = tk.StringVar()
        ttk.Label(frame, text="Usuário:").grid(row=1, column=0, sticky=tk.W)
        self.usuario_combobox = ttk.Combobox(frame, textvariable=self.usuario_var)
        self.usuario_combobox.grid(row=1, column=1, padx=5, pady=2, sticky=tk.EW)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=0, column=2, padx=5, rowspan=2)

        # Botões empilhados verticalmente
        ttk.Button(btn_frame, text="Adicionar Cliente", width=16, command=self.adicionar_cliente).pack(
            side=tk.TOP, fill=tk.X, pady=2
        )
        ttk.Button(btn_frame, text="Iniciar Cliente", width=5, command=self.selecionar_cliente).pack(
            side=tk.TOP, fill=tk.X, pady=2
        )

    def atualizar_usuarios_combobox(self, event=None):
        """
        Atualiza a lista de usuários no combobox de usuários quando um cliente é selecionado.
        """
        cliente = self.cliente_var.get()
        usuarios = self.carregar_usuarios_para_cliente(cliente)
        self.usuario_combobox["values"] = usuarios

    def adicionar_cliente(self):
        novo_cliente = self.cliente_var.get()
        if novo_cliente and novo_cliente not in self.clientes:
            clientes_file = self.base_dir / "clientes.txt"
            with open(clientes_file, "a", encoding="utf-8") as f:
                f.write(f"{novo_cliente}\n")
            self.clientes.append(novo_cliente)
            self.cliente_combobox["values"] = self.clientes
            self.cliente_var.set("")

    def calcular_md5(self, conteudo):
        """
        Calcula o MD5 de um conteúdo.
        """
        return hashlib.md5(conteudo.encode("utf-8")).hexdigest()


    def selecionar_cliente(self):
        novo_cliente = self.cliente_var.get()
        usuario = self.usuario_var.get()
        if not novo_cliente:
            return

        if self.current_atendimento and not self.current_atendimento["finalizado"]:
            self.salvar_atendimento_temporario()

        # Salva o usuário no arquivo do cliente
        self.salvar_usuario_para_cliente(novo_cliente, usuario)

        # Verifica se o arquivo "Cliente-Usuario.txt" existe
        cliente = self.cliente_var.get().strip()
        usuario = self.usuario_var.get().strip()
        if cliente and usuario:
            filename = f"{cliente}-{usuario}.txt".replace("/", "_")
            file_path = self.dados_usuario_dir / filename

            if file_path.exists():
                # Verifica se o arquivo de snapshot já existe
                snapshot_file = self.dados_usuario_dir / f"{cliente}-{usuario}.old"
                if snapshot_file.exists():
                    # Lê o conteúdo do último snapshot
                    with open(snapshot_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        if lines:
                            # Obtém o MD5 do último snapshot (última linha antes dos asteriscos)
                            last_md5 = None
                            for line in reversed(lines):
                                if line.startswith("MD5:"):
                                    last_md5 = line.strip().split(": ")[1]
                                    break

                            # Lê o conteúdo atual do arquivo "Cliente-Usuario.txt"
                            with open(file_path, "r", encoding="utf-8") as f2:
                                current_content = f2.read().strip()

                            # Calcula o MD5 do conteúdo atual
                            current_md5 = self.calcular_md5(current_content)

                            # Compara os MD5s
                            if last_md5 != current_md5:
                                # Adiciona um novo snapshot
                                snapshot_number = len(lines) // 7 + 1  # Calcula o número do snapshot
                                if snapshot_number > 7:
                                    # Remove os snapshots mais antigos
                                    lines = lines[-(7 * 6):]  # Mantém apenas os últimos 7 snapshots
                                    snapshot_number = 7

                                # Adiciona o novo snapshot
                                snapshot = (
                                    f"Espelhado na data: {datetime.now().strftime('%d/%m/%Y')}"
                                    f" Hora: {datetime.now().strftime('%H:%M')}\n\n\n"
                                    f"{current_content}\n\n\n"
                                    f"MD5: {current_md5}\n"
                                    "***********************************\n"
                                )
                                lines.append(snapshot)

                                # Salva o arquivo de snapshot atualizado
                                with open(snapshot_file, "w", encoding="utf-8") as f3:
                                    f3.writelines(lines)
                else:
                    # Cria o arquivo de snapshot e adiciona o primeiro snapshot
                    with open(file_path, "r", encoding="utf-8") as f:
                        current_content = f.read().strip()

                    # Calcula o MD5 do conteúdo atual
                    current_md5 = self.calcular_md5(current_content)

                    snapshot = (
                        f"“Temporário” “1” “data: {datetime.now().strftime('%d/%m/%Y')}” "
                        f"“Hora: {datetime.now().strftime('%H:%M')}”\n\n"
                        f"{current_content}\n"
                        f"MD5: {current_md5}\n"
                        "***********************************\n"
                    )
                    with open(snapshot_file, "w", encoding="utf-8") as f2:
                        f2.write(snapshot)

            # Carrega os dados do usuário no campo de texto
            self.dados_usuario_text.delete("1.0", tk.END)
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    self.dados_usuario_text.insert(tk.END, f.read())

        # Inicia o novo atendimento
        self.iniciar_novo_atendimento()

        # Define o cliente e usuário selecionados
        self.cliente_var.set(novo_cliente)
        self.usuario_var.set(usuario)
        self.atualizar_interface_atendimento()

    def salvar_usuario_para_cliente(self, cliente, usuario):
        """
        Salva o usuário no arquivo de usuários do cliente.
        """
        if not cliente or not usuario:
            return

        cliente_file = self.usuarios_dir / f"{cliente}.txt"
        usuarios = set()

        # Carrega os usuários existentes, se o arquivo existir
        if cliente_file.exists():
            with open(cliente_file, "r", encoding="utf-8") as f:
                usuarios = set(line.strip() for line in f.readlines())

        # Adiciona o novo usuário
        usuarios.add(usuario)

        # Salva a lista de usuários no arquivo
        with open(cliente_file, "w", encoding="utf-8") as f:
            f.write("\n".join(usuarios))

        # Verifica se o arquivo "Cliente-Usuario.txt" existe
        cliente = self.cliente_var.get().strip()
        usuario = self.usuario_var.get().strip()
        if cliente and usuario:
            filename = f"{cliente}-{usuario}.txt".replace("/", "_")
            file_path = self.dados_usuario_dir / filename
            snapshot_file = self.dados_usuario_dir / f"{cliente}-{usuario}.old"

            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    current_content = f.read().strip()

                # Calcula o MD5 do conteúdo atual
                current_md5 = self.calcular_md5(current_content)

                # Determina o número do próximo espelhamento
                espelhamento_num = 1
                if snapshot_file.exists():
                    with open(snapshot_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        # Conta quantos espelhamentos já existem
                        espelhamento_num = sum(1 for line in lines if "Espelhamento:" in line) + 1

                # Formata o novo snapshot com o padrão solicitado
                snapshot = (
                    f"Espelhamento: {espelhamento_num}\n"
                    f"Data: {datetime.now().strftime('%d/%m/%Y')}\n"
                    f"Hora: {datetime.now().strftime('%H:%M')}\n\n"
                    f"{current_content}\n\n"
                    f"MD5: {current_md5}\n"
                    "***********************************\n"
                )

                # Adiciona o novo snapshot ao arquivo
                with open(snapshot_file, "a", encoding="utf-8") as f:
                    f.write(snapshot)

    def carregar_usuarios_para_cliente(self, cliente):
        """
        Carrega os usuários vinculados ao cliente.
        """
        if not cliente:
            return []

        cliente_file = self.usuarios_dir / f"{cliente}.txt"
        if cliente_file.exists():
            with open(cliente_file, "r", encoding="utf-8") as f:
                return [line.strip() for line in f.readlines()]
        return []


    def criar_secao_atendimento(self, parent):
        self.atendimento_frame = ttk.LabelFrame(parent, text="Atendimento Atual")
        self.atendimento_frame.pack(fill=tk.X, pady=5)

        self.info_frame = ttk.Frame(self.atendimento_frame)
        self.info_frame.grid(row=0, column=0, columnspan=2, sticky=tk.W)

        ttk.Label(self.info_frame, text="Data Inicial:").grid(row=0, column=0)
        self.data_inicial_label = ttk.Label(self.info_frame, text="")
        self.data_inicial_label.grid(row=0, column=1, padx=5)

        ttk.Label(self.info_frame, text="Hora Inicial:").grid(row=0, column=2)
        self.hora_inicial_label = ttk.Label(self.info_frame, text="")
        self.hora_inicial_label.grid(row=0, column=3, padx=5)

        ttk.Label(self.atendimento_frame, text="Problema a resolver:").grid(
            row=1, column=0, sticky=tk.W
        )
        self.problema_entry = scrolledtext.ScrolledText(
            self.atendimento_frame, height=4, width=45
        )
        self.problema_entry.grid(row=2, column=0, columnspan=2, padx=5, pady=2)
        # Botão direito abre menu
        self.problema_entry.bind("<Button-3>", self.criar_menu_contexto)
        # Adiciona binding para salvar em tempo real
        self.problema_entry.bind("<KeyRelease>", lambda e: self.salvar_campos_temporarios())

        ttk.Label(self.atendimento_frame, text="Tarefa realizada:").grid(
            row=3, column=0, sticky=tk.W
        )
        self.tarefa_entry = scrolledtext.ScrolledText(
            self.atendimento_frame, height=4, width=45
        )
        self.tarefa_entry.grid(row=4, column=0, columnspan=2, padx=5, pady=2)
        # Botão direito abre menu
        self.tarefa_entry.bind("<Button-3>", self.criar_menu_contexto)
        # Adiciona binding para salvar em tempo real
        self.tarefa_entry.bind("<KeyRelease>", lambda e: self.salvar_campos_temporarios())

        # Restante do código permanece igual...
        self.dynamic_frame = ttk.Frame(self.atendimento_frame)
        self.dynamic_frame.grid(row=5, column=0, columnspan=2, pady=5)

        self.btn_frame = ttk.Frame(self.atendimento_frame)
        self.btn_frame.grid(row=6, column=0, columnspan=2, pady=5)

        self.iniciar_novo_atendimento()

    def salvar_campos_temporarios(self):
        """Salva apenas os campos de problema e tarefa em tempo real"""
        if not hasattr(self, 'current_atendimento') or self.current_atendimento is None:
            return

        cliente = self.cliente_var.get().strip()
        usuario = self.usuario_var.get().strip()

        # Verifica se temos cliente e usuário válidos
        if not cliente or not usuario:
            return

        # Atualiza os campos no atendimento atual
        self.current_atendimento["problema"] = self.problema_entry.get("1.0", tk.END).strip()
        self.current_atendimento["tarefa"] = self.tarefa_entry.get("1.0", tk.END).strip()

        # Cria a chave composta para o atendimento temporário
        chave_composta = f"{cliente} – {usuario}"

        # Atualiza ou cria a entrada nos atendimentos temporários
        if chave_composta in self.tmp_atendimentos:
            self.tmp_atendimentos[chave_composta]["problema"] = self.current_atendimento["problema"]
            self.tmp_atendimentos[chave_composta]["tarefa"] = self.current_atendimento["tarefa"]
        else:
            self.tmp_atendimentos[chave_composta] = {
                "cliente": cliente,
                "usuario": usuario,
                "problema": self.current_atendimento["problema"],
                "tarefa": self.current_atendimento["tarefa"],
                "eventos": self.eventos if hasattr(self, 'eventos') else [],
                "estado": self.estado_atual if hasattr(self, 'estado_atual') else ESTADOS[0],
            }

        # Salva no arquivo temporário
        self.salvar_tmp_atendimentos()


    def iniciar_novo_atendimento(self):
        cliente = self.cliente_var.get().strip()
        usuario = self.usuario_var.get().strip()
        # Verifica se o cliente e o usuário não estão vazios
        if cliente and usuario:
            chave_composta = f"{cliente} – {usuario}"
            if chave_composta in self.tmp_atendimentos:
                self.carregar_atendimento_temporario(chave_composta)
            else:
                self.current_atendimento = {
                    "cliente": cliente,
                    "usuario": usuario,
                    "problema": "",
                    "tarefa": "",
                    "eventos": [],
                    "finalizado": False,
                }
                self.eventos = []
                self.estado_atual = ESTADOS[0]
                self.problema_entry.delete("1.0", tk.END)
                self.tarefa_entry.delete("1.0", tk.END)
                self.atualizar_interface_atendimento()

    def atualizar_interface_atendimento(self):
        for widget in self.dynamic_frame.winfo_children():
            widget.destroy()

        inicio_evento = next((e for e in self.eventos if e["tipo"] == "inicio"), None)
        if inicio_evento:
            self.data_inicial_label.config(
                text=inicio_evento["data"].strftime("%d/%m/%Y")
            )
            self.hora_inicial_label.config(text=inicio_evento["hora"].strftime("%H:%M"))
        else:
            self.data_inicial_label.config(text="")
            self.hora_inicial_label.config(text="")

        if self.estado_atual == "inicio":
            self.criar_interface_inicio()
        elif self.estado_atual == "em_andamento":
            self.criar_interface_em_andamento()
        elif self.estado_atual == "pausado":
            self.criar_interface_pausado()
        elif self.estado_atual == "finalizado":
            self.criar_interface_finalizado()

    def criar_interface_inicio(self):
        ttk.Label(self.dynamic_frame, text="Data:").grid(row=0, column=0)
        self.data_inicio = ttk.Entry(self.dynamic_frame)
        self.data_inicio.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.data_inicio.grid(row=0, column=1)

        ttk.Label(self.dynamic_frame, text="Início:").grid(row=1, column=0)
        self.hora_inicio = ttk.Entry(self.dynamic_frame)
        self.hora_inicio.insert(0, datetime.now().strftime("%H:%M"))
        self.hora_inicio.grid(row=1, column=1)

        ttk.Button(
            self.dynamic_frame,
            text="Iniciar Atendimento",
            command=self.iniciar_atendimento,
        ).grid(row=4, columnspan=2)

    def iniciar_atendimento(self):
        cliente = self.cliente_var.get().strip()
        if not cliente:
            messagebox.showerror("Erro", "Selecione um Cliente antes de iniciar o atendimento.")
            return

        if not hasattr(self, 'current_atendimento') or self.current_atendimento is None:
            messagebox.showwarning("Aviso", "Clique em 'Iniciar Cliente' antes de iniciar o atendimento.")
            return

        try:
            data = datetime.strptime(self.data_inicio.get(), "%d/%m/%Y").date()
            hora = datetime.strptime(self.hora_inicio.get(), "%H:%M").time()
            self.eventos.append({"tipo": "inicio", "data": data, "hora": hora})
            self.estado_atual = ESTADOS[1]
            self.salvar_atendimento_temporario()  # Salva o estado atualizado
            self.atualizar_interface_atendimento()

        except ValueError:
            messagebox.showerror("Erro", "Formato de data/hora inválido!")

    def criar_interface_em_andamento(self):
        # Campos para data e hora da ação
        ttk.Label(self.dynamic_frame, text="Data da Ação:").grid(
            row=0, column=0, sticky=tk.W
        )
        self.data_acao = ttk.Entry(self.dynamic_frame)
        self.data_acao.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.data_acao.grid(row=0, column=1, sticky=tk.W, pady=2)

        ttk.Label(self.dynamic_frame, text="Hora da Ação:").grid(
            row=1, column=0, sticky=tk.W
        )
        self.hora_acao = ttk.Entry(self.dynamic_frame)
        self.hora_acao.insert(0, datetime.now().strftime("%H:%M"))
        self.hora_acao.grid(row=1, column=1, sticky=tk.W, pady=2)

        # Botões de ação
        ttk.Label(self.dynamic_frame, text="Selecione a próxima ação:").grid(
            row=2, columnspan=2, pady=5
        )

        btn_frame = ttk.Frame(self.dynamic_frame)
        btn_frame.grid(row=3, columnspan=2)

        ttk.Button(btn_frame, text="Pausar", command=self.preparar_pausa).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(btn_frame, text="Finalizar", command=self.preparar_finalizacao).pack(
            side=tk.LEFT, padx=5
        )

    def preparar_pausa(self):
        try:
            data_str = self.data_acao.get() or datetime.now().strftime("%d/%m/%Y")
            hora_str = self.hora_acao.get() or datetime.now().strftime("%H:%M")

            data_pausa = datetime.strptime(data_str, "%d/%m/%Y").date()
            hora_pausa = datetime.strptime(hora_str, "%H:%M").time()

            self.mudar_estado("pausado", data_pausa, hora_pausa)
            self.salvar_tmp_atendimentos()  # Salva o estado atualizado

        except ValueError as e:
            messagebox.showerror("Erro", f"Formato inválido: {str(e)}")

    def preparar_finalizacao(self):
        confirmacao = messagebox.askyesno(
            "Confirmar Finalização", "Tem certeza que deseja finalizar o atendimento?"
        )

        if confirmacao:
            try:
                data_str = self.data_acao.get() or datetime.now().strftime("%d/%m/%Y")
                hora_str = self.hora_acao.get() or datetime.now().strftime("%H:%M")

                data_fim = datetime.strptime(data_str, "%d/%m/%Y").date()
                hora_fim = datetime.strptime(hora_str, "%H:%M").time()

                self.mudar_estado("finalizado", data_fim, hora_fim)
                self.salvar_tmp_atendimentos()  # Salva o estado atualizado

            except ValueError as e:
                messagebox.showerror("Erro", f"Formato inválido: {str(e)}")
        else:
            messagebox.showinfo("Cancelado", "Finalização cancelada pelo usuário.")

    def mudar_estado(self, novo_estado, data=None, hora=None):
        if novo_estado == "pausado":
            self.eventos.append({"tipo": "pausa", "data": data, "hora": hora})
        elif novo_estado == "finalizado":
            self.eventos.append({"tipo": "fim", "data": data, "hora": hora})

        self.estado_atual = novo_estado
        self.atualizar_interface_atendimento()

    def criar_interface_pausado(self):
        ttk.Label(self.dynamic_frame, text="Data da Pausa:").grid(row=0, column=0)
        self.data_pausa = ttk.Entry(self.dynamic_frame)
        self.data_pausa.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.data_pausa.grid(row=0, column=1)

        ttk.Label(self.dynamic_frame, text="Hora da Pausa:").grid(row=1, column=0)
        self.hora_pausa = ttk.Entry(self.dynamic_frame)
        self.hora_pausa.insert(0, datetime.now().strftime("%H:%M"))
        self.hora_pausa.grid(row=1, column=1)

        ttk.Label(self.dynamic_frame, text="Ação:").grid(row=2, column=0)
        btn_frame = ttk.Frame(self.dynamic_frame)
        btn_frame.grid(row=2, column=1)
        ttk.Button(
            btn_frame,
            text="Retomar Atendimento",
            command=lambda: self.registrar_retomada(mesma_data=True),
        ).pack(side=tk.LEFT)

    def registrar_retomada(self, mesma_data=True):
        try:
            data_pausa = datetime.strptime(self.data_pausa.get(), "%d/%m/%Y")
            hora_pausa = datetime.strptime(self.hora_pausa.get(), "%H:%M").time()
            data_retomada = datetime.strptime(self.data_pausa.get(), "%d/%m/%Y").date()
            hora_retomada = datetime.strptime(self.hora_pausa.get(), "%H:%M").time()

            # Adiciona o evento de retomada
            self.eventos.append(
                {"tipo": "retomada", "data": data_retomada, "hora": hora_retomada}
            )

            # Atualiza o estado para "em_andamento"
            self.estado_atual = ESTADOS[1]

            # Atualiza a interface e salva o estado
            self.atualizar_interface_atendimento()
            self.salvar_tmp_atendimentos()  # Salva o estado atualizado

        except ValueError:
            messagebox.showerror("Erro", "Formato de data/hora inválido!")

    def criar_interface_finalizado(self):
        ttk.Label(self.dynamic_frame, text="Data Final:").grid(row=0, column=0)
        self.data_fim = ttk.Entry(self.dynamic_frame)
        self.data_fim.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.data_fim.grid(row=0, column=1)

        ttk.Label(self.dynamic_frame, text="Hora Final:").grid(row=1, column=0)
        self.hora_fim = ttk.Entry(self.dynamic_frame)
        self.hora_fim.insert(0, datetime.now().strftime("%H:%M"))
        self.hora_fim.grid(row=1, column=1)

        ttk.Button(
            self.dynamic_frame,
            text="Calcular Tempo Total",
            command=self.calcular_tempo_total,
        ).grid(row=2, columnspan=2)

    def calcular_tempo_total(self):
        try:
            data_fim = datetime.strptime(self.data_fim.get(), "%d/%m/%Y")
            hora_fim = datetime.strptime(self.hora_fim.get(), "%H:%M").time()

            tempo_total = timedelta()
            inicio = None

            for evento in self.eventos:
                dt = datetime.combine(evento["data"], evento["hora"])
                if evento["tipo"] == "inicio":
                    inicio = dt
                elif evento["tipo"] == "pausa" and inicio:
                    tempo_total += dt - inicio
                    inicio = None
                elif evento["tipo"] == "retomada":
                    inicio = dt
                elif evento["tipo"] == "fim" and inicio:
                    tempo_total += dt - inicio
                    inicio = None

            horas = int(tempo_total.total_seconds() // 3600)
            minutos = int((tempo_total.total_seconds() % 3600) // 60)

            self.current_atendimento["tempo_total"] = tempo_total
            self.current_atendimento["finalizado"] = True

            ttk.Label(
                self.dynamic_frame, text=f"Tempo Total: {horas:02d}:{minutos:02d}"
            ).grid(row=3, columnspan=2)

            self.salvar_atendimento()
            chave_composta = f"{self.current_atendimento['cliente']} – {self.current_atendimento['usuario']}"
            if chave_composta in self.tmp_atendimentos:
                del self.tmp_atendimentos[chave_composta]

            # Limpar o campo "Dados do Usuário"
            self.dados_usuario_text.delete("1.0", tk.END)

            self.current_atendimento = None
            self.eventos = []
            self.estado_atual = ESTADOS[0]

            self.cliente_var.set("")
            self.usuario_var.set("")
            self.problema_entry.delete("1.0", tk.END)
            self.tarefa_entry.delete("1.0", tk.END)

            self.salvar_tmp_atendimentos()
            self.atualizar_lista_abertos()
            self.atualizar_interface_atendimento()
        except ValueError as e:
            messagebox.showerror("Erro", f"Erro no cálculo: {str(e)}")

    def salvar_atendimento(self):
        try:
            self.current_atendimento.update(
                {
                    "cliente": self.cliente_var.get(),
                    "usuario": self.usuario_var.get(),
                    "problema": self.problema_entry.get("1.0", tk.END).strip(),
                    "tarefa": self.tarefa_entry.get("1.0", tk.END).strip(),
                    "eventos": self.eventos,
                    "finalizado": self.estado_atual == "finalizado",
                }
            )

            if self.current_atendimento["finalizado"]:
                self.salvar_atendimento_finalizado()
            else:
                self.salvar_atendimento_aberto()

            messagebox.showinfo("Sucesso", "Atendimento salvo com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar atendimento: {str(e)}")

    def salvar_atendimento_finalizado(self):
        inicio = next(e for e in self.eventos if e["tipo"] == "inicio")
        data = inicio["data"]

        # Obtém o próximo número de atendimento (já formatado como "operador - numero")
        numero_atendimento_completo = self.obter_proximo_numero_atendimento()

        # Extrai apenas o número do atendimento (remove o operador)
        numero_atendimento = numero_atendimento_completo.split(" - ")[-1]

        self.current_atendimento["numero_atendimento"] = numero_atendimento_completo

        # Determina o tipo de atendimento
        tipo_atendimento = "Presencial" if hasattr(self, 'atendimento_presencial') and self.atendimento_presencial else "Remoto"
        self.current_atendimento["tipo"] = tipo_atendimento

        # Salva no arquivo todos.txt dentro da pasta atendimentos/ano/mes
        ano_dir = self.atendimentos_dir / str(data.year)
        mes_dir = ano_dir / data.strftime("%B").lower()
        mes_dir.mkdir(parents=True, exist_ok=True)

        todos_path = mes_dir / "todos.txt"
        with open(todos_path, "a", encoding="utf-8") as f:
            f.write(self.formatar_atendimento(self.current_atendimento))

        # Salva no arquivo do cliente
        cliente_path = mes_dir / f"{self.current_atendimento['cliente']}.txt"
        with open(cliente_path, "a", encoding="utf-8") as f:
            f.write(self.formatar_atendimento(self.current_atendimento))

        # Cria ou atualiza o arquivo status.txt com o novo formato
        status_path = mes_dir / "status.txt"
        status_entry = (
            "**********************************\n"
            f"Cadastro do Operador: {self.numero_operador}\n"
            f"Número do atendimento: {numero_atendimento}\n"  # Agora só o número
            f"Situação: Não Processado\n"
            f"Tipo: {tipo_atendimento}\n"
            "**********************************\n\n"
        )

        # Verifica se o arquivo já existe para evitar duplicatas
        if status_path.exists():
            with open(status_path, "r", encoding="utf-8") as f:
                content = f.read()
                if numero_atendimento not in content:  # Evita duplicar entradas
                    with open(status_path, "a", encoding="utf-8") as f:
                        f.write(status_entry)
        else:
            with open(status_path, "w", encoding="utf-8") as f:
                f.write(status_entry)

    def salvar_atendimento_aberto(self):
        self.salvar_atendimento_temporario()
        tmp_path = self.base_dir / "tmp.txt"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(
                self.atendimentos_abertos, f, indent=2, default=self.serializar_dados
            )

    def formatar_atendimento(self, atendimento):
        """
        Formata os dados do atendimento para salvar no arquivo.
        """
        eventos_str = []
        for evento in atendimento["eventos"]:
            data_str = evento["data"].strftime("%d/%m/%Y")
            hora_str = evento["hora"].strftime("%H:%M")
            # Sempre formata como INÍCIO (com acento) no arquivo
            tipo = "INÍCIO" if evento["tipo"] == "inicio" else evento["tipo"].upper()
            eventos_str.append(f"{tipo}: {data_str} {hora_str}")

        # Restante da função permanece igual...
        tempo_total = atendimento.get('tempo_total', timedelta())
        if not isinstance(tempo_total, timedelta):
            tempo_total = timedelta()

        horas = int(tempo_total.total_seconds() // 3600)
        minutos = int((tempo_total.total_seconds() % 3600) // 60)

        tipo_atendimento = atendimento.get("tipo", "Remoto")

        return (
            "**********************************\n"
            f"Atendente - Nº do Atendimento: {atendimento.get('numero_atendimento', 'N/A')}\n"
            f"Tipo: {tipo_atendimento}\n"
            f"Nome do Cliente: {atendimento['cliente']}\n"
            f"Usuário: {atendimento.get('usuario', '')}\n\n"
            f"Problema a resolver: {atendimento['problema']}\n\n"
            f"Tarefa realizada: {atendimento['tarefa']}\n\n"
            "Histórico de Eventos:\n" + "\n".join(eventos_str) + "\n\n"
            f"Tempo Total: {horas:02d}:{minutos:02d}\n\n"
            "**********************************\n\n"
        )

    def serializar_dados(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, time):
            return obj.strftime("%H:%M")
        if isinstance(obj, timedelta):
            return obj.total_seconds()
        raise TypeError(f"Tipo não serializável: {type(obj)}")

    def criar_secao_historico(self, parent):
        # Cria um estilo para a Treeview com fonte maior
        style = ttk.Style()
        style.configure("Treeview", font=('Liberation Serif', 11))
        style.configure("Treeview.Heading", font=('Helvetica', 10, 'bold'))  # Para os cabeçalhos

        frame = ttk.LabelFrame(parent, text="Histórico de Atendimentos")
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        nav_frame = ttk.Frame(frame)
        nav_frame.pack(fill=tk.X, pady=2)

        ttk.Label(nav_frame, text="Ano:").pack(side=tk.LEFT)
        self.ano_combobox = ttk.Combobox(nav_frame, width=5)
        self.ano_combobox.pack(side=tk.LEFT, padx=5)

        ttk.Label(nav_frame, text="Mês:").pack(side=tk.LEFT)
        self.mes_combobox = ttk.Combobox(nav_frame, width=10)
        self.mes_combobox.pack(side=tk.LEFT, padx=5)

        ttk.Button(nav_frame, text="Carregar", command=self.carregar_historico).pack(
            side=tk.LEFT
        )

        # Adiciona um separador entre os botões
        ttk.Separator(nav_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)

        # Adiciona o novo botão Detalhes
        ttk.Button(nav_frame, text="Detalhes", command=self.abrir_detalhes_selecionado).pack(
            side=tk.LEFT
        )

    # Adiciona um separador entre os botões
        ttk.Separator(nav_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)

        # Adiciona o novo botão Buscar
        ttk.Button(nav_frame, text="Buscar", command=self.criar_janela_busca).pack(
            side=tk.LEFT, padx=5
        )

        # Frame para conter a Treeview e as barras de rolagem
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # Configurar pesos para expansão
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        # Barra de rolagem vertical
        yscroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Barra de rolagem horizontal
        xscroll = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        xscroll.pack(side=tk.BOTTOM, fill=tk.X)

        # Define as colunas antes de criar a Treeview
        self.colunas = [
            ("Cliente", 220, 220, True),    # Nome, largura inicial, largura mínima, redimensionável
            ("Data", 80, 80, False),       # Coluna Data fixa
            ("Problema", 220, 220, True),
            ("Tarefa", 170, 170, True),
            ("Tempo", 80, 80, False),      # Coluna Tempo fixa
        ]

        self.tree = ttk.Treeview(
            tree_frame,
            columns=[col[0] for col in self.colunas],
            show="headings",
            yscrollcommand=yscroll.set,
            xscrollcommand=xscroll.set
        )
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Configuração das colunas
        for col, width, minwidth, resizable in self.colunas:
            self.tree.heading(col, text=col)
            if resizable:
                self.tree.column(col, width=width, anchor=tk.W, stretch=True, minwidth=minwidth)
            else:
                self.tree.column(col, width=width, anchor=tk.W, stretch=False, minwidth=width)

        # Configura tags para diferentes estados
        self.tree.tag_configure('processado', foreground='green')
        self.tree.tag_configure('aberto', foreground='red', font=('Helvetica', 10, 'bold'))

        # Configurar redimensionamento de colunas
        self.tree.bind("<ButtonRelease-1>", self.salvar_larguras_colunas)
        self.tree.bind("<B1-Motion>", self.salvar_larguras_colunas)

        self.tree.bind("<<TreeviewSelect>>", self.atualizar_selecao_historico)
        self.tree.bind("<Double-1>", self.visualizar_detalhes)
        self.atualizar_navegacao_temporal()

        # Carregar configurações salvas das colunas
        self.carregar_configuracoes_colunas()

    def carregar_configuracoes_colunas(self):
        """Carrega as larguras das colunas salvas, respeitando os mínimos"""
        if not hasattr(self, 'colunas'):
            return  # Se colunas não foi definido ainda, ignora

        colunas_path = self.config_dir / "colunas_historico.json"
        try:
            if colunas_path.exists():
                with open(colunas_path, "r", encoding="utf-8") as f:
                    colunas_config = json.load(f)
                    for col, config in colunas_config.items():
                        # Encontra a configuração desta coluna
                        col_config = next((c for c in self.colunas if c[0] == col), None)
                        if col_config:
                            # Usa o maior valor entre o salvo e o mínimo
                            width = max(config['width'], col_config[2])
                            self.tree.column(col, width=width)
        except Exception as e:
            print(f"Erro ao carregar configurações das colunas: {e}")

    def salvar_larguras_colunas(self, event=None):
        """Salva as larguras atuais das colunas"""
        colunas_path = self.config_dir / "colunas_historico.json"
        try:
            colunas_config = {}
            for col in self.tree["columns"]:
                width = self.tree.column(col, 'width')
                colunas_config[col] = {'width': width}

            with open(colunas_path, "w", encoding="utf-8") as f:
                json.dump(colunas_config, f, indent=2)
        except Exception as e:
            print(f"Erro ao salvar configurações das colunas: {e}")

    def atualizar_navegacao_temporal(self):
        # Obtém o ano e o mês atuais
        ano_atual = datetime.now().year
        mes_atual = datetime.now().strftime("%B")  # Nome completo do mês (ex: "Janeiro")

        # Obtém os anos disponíveis
        anos = set()
        for entry in self.atendimentos_dir.iterdir():
            if entry.is_dir() and entry.name.isdigit():
                anos.add(int(entry.name))
        self.ano_combobox["values"] = sorted(anos, reverse=True)

        # Define o ano atual como valor padrão
        if anos:
            self.ano_combobox.set(ano_atual)

        # Define os meses disponíveis
        meses = [
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
        ]
        self.mes_combobox["values"] = meses

        # Define o mês atual como valor padrão
        self.mes_combobox.set(mes_atual)

    def salvar_selecao_atual(self, event=None):
        """Salva a seleção atual usando o número do atendimento como identificador"""
        selecionados = self.tree.selection()
        if not selecionados:
            return

        item = selecionados[0]
        index = self.tree.index(item)

        if index < len(self.current_historico):
            atendimento = self.current_historico[index]
            numero_atendimento = atendimento.get("numero_atendimento", "")

            if numero_atendimento:
                with open(self.config_dir / "ultima_selecao.json", 'w', encoding='utf-8') as f:
                    json.dump({"numero_atendimento": numero_atendimento}, f)

    def carregar_ultima_selecao(self):
        """Carrega a última seleção usando o número do atendimento como identificador"""
        try:
            arquivo_selecao = self.config_dir / "ultima_selecao.json"
            if not arquivo_selecao.exists():
                return

            with open(arquivo_selecao, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                numero_atendimento = dados.get("numero_atendimento", "")

                if not numero_atendimento:
                    return

                # Procura pelo atendimento com o número correspondente
                for i, atendimento in enumerate(self.current_historico):
                    if atendimento.get("numero_atendimento", "") == numero_atendimento:
                        # Seleciona o item correspondente na treeview
                        if i < len(self.tree.get_children()):
                            item = self.tree.get_children()[i]
                            self.tree.selection_set(item)
                            self.tree.focus(item)
                            self.tree.see(item)
                        return

        except Exception as e:
            print(f"Erro ao carregar seleção: {e}")

    def verificar_status_atendimento(self, atendimento):
        """Verifica o status de um atendimento no arquivo status.txt na NOVA estrutura"""
        numero_atendimento_completo = atendimento.get('numero_atendimento', '')
        if not numero_atendimento_completo:
            return "Não Processado"  # Padrão para atendimentos antigos

        numero_atendimento = numero_atendimento_completo.split(' - ')[-1]
        data_inicio = atendimento["eventos"][0]["data"]

        # Caminho na NOVA estrutura
        ano_dir = self.atendimentos_dir / str(data_inicio.year)
        mes_dir = ano_dir / data_inicio.strftime("%B").lower()
        status_path = mes_dir / "status.txt"

        if not status_path.exists():
            return "Não Processado"

        with open(status_path, "r", encoding="utf-8") as f:
            content = f.read()

        blocos = content.split("**********************************\n")
        for bloco in blocos:
            if f"Número do atendimento: {numero_atendimento}" in bloco:
                if "Situação: Processado" in bloco:
                    return "Processado"
                elif "Situação: Não Processado" in bloco:
                    return "Não Processado"
                elif "Situação: Cancelado" in bloco:
                    return "Cancelado"

        return "Não Processado"

    def carregar_historico(self):
        """Carrega o histórico e aplica cores baseadas no status"""
        # Primeiro carregamos todo o conteúdo normalmente
        ano = self.ano_combobox.get()
        mes = self.mes_combobox.get().lower()

        if not ano or not mes:
            return

        # Limpa a lista de histórico
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.current_historico = []

        # Verifica se o diretório do mês existe dentro da pasta atendimentos
        mes_dir = self.atendimentos_dir / ano / mes
        todos_path = mes_dir / "todos.txt"

        if not todos_path.exists():
            if not self.carregamento_inicial:
                messagebox.showinfo("Sem dados", f"Não há dados para {mes.capitalize()} de {ano}")
            return

        # Configura a tag para atendimentos processados
        self.tree.tag_configure('processado', foreground='green')
        self.tree.tag_configure('aberto', foreground='red', font=('Helvetica', 10, 'bold'))
        self.tree.tag_configure('presencial', font=('Helvetica', 10, 'bold'))
        self.tree.tag_configure('presencial_processado', foreground='green', font=('Helvetica', 10, 'bold'))

        # Carrega o histórico do arquivo todos.txt
        with open(todos_path, "r", encoding="utf-8") as f:
            atendimentos = self.parse_arquivo_historico(f.read())
            self.current_historico = atendimentos

            for atend in atendimentos:
                cliente_usuario = f"{atend['cliente']} – {atend.get('usuario', '')}"
                data_str = (
                    atend["eventos"][0]["data"].strftime("%d/%m/%Y")
                    if atend["eventos"]
                    else "N/A"
                )
                problema_short = (
                    (atend["problema"][:50] + "...")
                    if len(atend["problema"]) > 50
                    else atend["problema"]
                )
                tarefa_short = (
                    (atend["tarefa"][:50] + "...")
                    if len(atend["tarefa"]) > 50
                    else atend["tarefa"]
                )
                tempo_total = atend.get("tempo_total", timedelta())
                if tempo_total:
                    horas = int(tempo_total.total_seconds() // 3600)
                    minutos = int((tempo_total.total_seconds() % 3600) // 60)
                    tempo_str = f"{horas:02d}:{minutos:02d}"
                else:
                    tempo_str = "N/A"

                # Verifica o status do atendimento
                status = self.verificar_status_atendimento(atend)
                tipo_atendimento = atend.get("tipo", "Remoto").lower()

                # Determina as tags a serem aplicadas
                tags = []

                if status == "Processado":
                    if tipo_atendimento == "presencial":
                        tags.append('presencial_processado')
                    else:
                        tags.append('processado')
                elif not atend.get("finalizado", True):  # Atendimentos em aberto
                    tags.append('aberto')
                elif tipo_atendimento == "presencial":
                    tags.append('presencial')

                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        cliente_usuario,
                        data_str,
                        problema_short,
                        tarefa_short,
                        tempo_str,
                    ),
                    tags=tuple(tags) if tags else ()
                )

        # Adiciona atendimentos em aberto do mês atual
        if datetime.now().strftime("%B").lower() == mes:
            for atend in self.tmp_atendimentos.values():
                cliente_usuario = f"{atend['cliente']} – {atend['usuario']}"
                data_str = (
                    atend["eventos"][0]["data"].strftime("%d/%m/%Y")
                    if atend["eventos"]
                    else "N/A"
                )
                problema_short = (
                    (atend["problema"][:50] + "...")
                    if len(atend["problema"]) > 50
                    else atend["problema"]
                )
                tarefa_short = (
                    (atend["tarefa"][:50] + "...")
                    if len(atend["tarefa"]) > 50
                    else atend["tarefa"]
                )
                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        cliente_usuario,
                        data_str,
                        problema_short,
                        tarefa_short,
                        "Em aberto",
                    ),
                    tags=("aberto",),
                )

        # Após carregar todos os itens, restaura a seleção
        self.carregar_ultima_selecao()

        # Atualiza o estado de carregamento
        if self.carregamento_inicial:
            self.carregamento_inicial = False

    def obter_selecao_atual(self):
        """Obtém todas as informações necessárias para restaurar a seleção"""
        selecionados = self.tree.selection()
        if not selecionados:
            return None

        item = selecionados[0]
        valores = self.tree.item(item, 'values')

        return {
            'item': item,
            'cliente': valores[0] if valores else None,
            'data': valores[1] if valores and len(valores) > 1 else None,
            'problema': valores[2] if valores and len(valores) > 2 else None
        }

    def restaurar_selecao(self, selecao_anterior):
        """Restaura a seleção com múltiplas estratégias de fallback"""
        if not selecao_anterior:
            return

        # Método 1: Tentar encontrar o mesmo item pelo cliente e data
        if selecao_anterior.get('cliente') and selecao_anterior.get('data'):
            for item in self.tree.get_children():
                valores = self.tree.item(item, 'values')
                if (valores and len(valores) > 1 and
                    valores[0] == selecao_anterior['cliente'] and
                    valores[1] == selecao_anterior['data']):
                    self.selecionar_item(item)
                    return

        # Método 2: Tentar encontrar apenas pelo cliente
        if selecao_anterior.get('cliente'):
            for item in self.tree.get_children():
                valores = self.tree.item(item, 'values')
                if valores and valores[0] == selecao_anterior['cliente']:
                    self.selecionar_item(item)
                    return

        # Método 3: Selecionar o primeiro item se disponível
        items = self.tree.get_children()
        if items:
            self.selecionar_item(items[0])

    def selecionar_item(self, item):
        """Seleciona um item com garantia de visibilidade"""
        self.tree.selection_set(item)
        self.tree.focus(item)
        self.tree.see(item)
        # Força o foco para garantir que a seleção seja visível
        self.tree.update_idletasks()
        self.root.update()

    def restaurar_selecao_historico(self, cliente_selecionado):
        """Tenta restaurar a seleção com base no nome do cliente"""
        if not cliente_selecionado:
            return

        # Procura pelo cliente na Treeview
        for item in self.tree.get_children():
            valores = self.tree.item(item)['values']
            if valores and valores[0] == cliente_selecionado:
                self.tree.selection_set(item)
                self.tree.focus(item)
                self.tree.see(item)  # Garante que o item está visível
                return

        # Se não encontrou, tenta selecionar o primeiro item
        items = self.tree.get_children()
        if items:
            self.tree.selection_set(items[0])
            self.tree.focus(items[0])

    def atualizar_selecao_historico(self, event):
        """Armazena a seleção atual quando o usuário seleciona um item"""
        selecionado = self.tree.selection()
        if selecionado:
            self.last_selected_historico = self.tree.item(selecionado[0])['values'][0]  # Armazena o cliente

    def parse_arquivo_historico(self, conteudo):
        atendimentos = []
        blocos = conteudo.split("**********************************\n")

        for bloco in blocos:
            if not bloco.strip():
                continue

            atend = {
                "eventos": [],
                "cliente": "",
                "usuario": "",
                "problema": "",
                "tarefa": "",
                "numero_atendimento": "N/A",
                "tipo": "Remoto"
            }
            lines = [line.strip() for line in bloco.split('\n') if line.strip()]

            for line in lines:
                if line.startswith("Atendente - Nº do Atendimento:"):
                    atend["numero_atendimento"] = line.split(": ", 1)[1].strip() if ": " in line else "N/A"
                elif line.startswith("Tipo:"):
                    atend["tipo"] = line.split(": ", 1)[1].strip() if ": " in line else "Remoto"
                elif line.startswith("Nome do Cliente:"):
                    atend["cliente"] = line.split(": ", 1)[1].strip() if ": " in line else ""
                elif line.startswith("Usuário:"):
                    atend["usuario"] = line.split(": ", 1)[1].strip() if ": " in line else ""
                elif line.startswith("Problema a resolver:"):
                    atend["problema"] = line.split(": ", 1)[1].strip() if ": " in line else ""
                elif line.startswith("Tarefa realizada:"):
                    atend["tarefa"] = line.split(": ", 1)[1].strip() if ": " in line else ""
                elif line.startswith("Histórico de Eventos:"):
                    break

            event_lines = []
            in_events = False
            for line in lines:
                if line.startswith("Histórico de Eventos:"):
                    in_events = True
                    continue
                if in_events and any(line.startswith(tipo) for tipo in ["INÍCIO:", "INICIO:", "PAUSA:", "RETOMADA:", "FIM:"]):
                    partes = line.split()
                    tipo = partes[0].replace(":", "").lower()
                    # Padroniza para "inicio" sem acento internamente
                    if tipo in ["início", "inicio"]:
                        tipo = "inicio"
                    data_str = partes[1]
                    hora_str = partes[2]
                    atend["eventos"].append({
                        "tipo": tipo,
                        "data": datetime.strptime(data_str, "%d/%m/%Y").date(),
                        "hora": datetime.strptime(hora_str, "%H:%M").time(),
                    })

            if "tempo_total" not in atend:
                atend["tempo_total"] = self.calcular_tempo_total_eventos(atend["eventos"])

            if atend["cliente"]:
                atendimentos.append(atend)

        return atendimentos

    def visualizar_detalhes(self, event):
        item = self.tree.selection()[0]
        index = self.tree.index(item)

        if index < len(self.current_historico):
            atendimento = self.current_historico[index]
        else:
            tmp_list = list(self.tmp_atendimentos.values())
            atendimento = tmp_list[index - len(self.current_historico)]

        original_atendimento = copy.deepcopy(atendimento)

        # Armazena o número do atendimento
        numero_atendimento = atendimento.get("numero_atendimento", "")

        detalhes_window = tk.Toplevel(self.root)
        detalhes_window.title("Detalhes do Atendimento")
        detalhes_window.geometry("720x580")

        # Armazena o número do atendimento na janela
        detalhes_window.numero_atendimento = numero_atendimento

        main_frame = ttk.Frame(detalhes_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        # Adiciona uma linha separadora
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        edit_button = ttk.Button(
            btn_frame,
            text="Editar",
            command=lambda: self.toggle_edit(detalhes_window, True),
        )
        edit_button.pack(side=tk.LEFT, padx=5)

        save_button = ttk.Button(
            btn_frame,
            text="Salvar",
            command=lambda: self.salvar_edicao(original_atendimento, detalhes_window),
        )
        save_button.pack(side=tk.LEFT, padx=5)
        save_button.config(state=tk.DISABLED)

        remove_button = ttk.Button(
            btn_frame,
            text="Remover este Atendimento",
            command=lambda: self.remover_atendimento(original_atendimento, detalhes_window),
        )
        remove_button.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="Copiar dados do atendimento",
            command=lambda: self.copiar_dados_do_atendimento(detalhes_window, original_atendimento)
        ).pack(side=tk.LEFT, padx=5)

        fields_frame = ttk.Frame(main_frame)
        fields_frame.pack(fill=tk.BOTH, expand=True)

        # Adiciona o botão de status
        self.status_btn = ttk.Button(
            btn_frame,
            text="Não Processado",
            style="Red.TButton",
            command=lambda: self.alternar_status_atendimento(detalhes_window, original_atendimento)
        )
        self.status_btn.pack(side=tk.LEFT, padx=5)

        # Configura o estilo dos botões de status
        style = ttk.Style()
        style.configure("Red.TButton", foreground="white", background="red", font=('Helvetica', 10, 'bold'))
        style.configure("Green.TButton", foreground="white", background="green", font=('Helvetica', 10, 'bold'))

        # Verifica o status atual e configura o botão
        self.verificar_status_botao(original_atendimento)

        # Adiciona uma linha separadora
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        # Frame para informações do atendimento (entre botões e campos)
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=5)

        # Adiciona os campos de informações do atendimento
        ttk.Label(info_frame, text="Atendente:", font=('Helvetica', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Label(info_frame, text=atendimento.get('numero_atendimento', 'N/A').split(' - ')[0],
                font=('Helvetica', 10)).grid(row=0, column=1, sticky=tk.W)

        ttk.Label(info_frame, text="Nº do atendimento:", font=('Helvetica', 10, 'bold')).grid(row=0, column=2, sticky=tk.W, padx=5)
        ttk.Label(info_frame, text=atendimento.get('numero_atendimento', 'N/A').split(' - ')[-1],
                font=('Helvetica', 10)).grid(row=0, column=3, sticky=tk.W)

        ttk.Label(info_frame, text="Tipo:", font=('Helvetica', 10, 'bold')).grid(row=0, column=4, sticky=tk.W, padx=5)
        tipo = atendimento.get('tipo', 'Remoto')  # Usa o tipo salvo ou 'Remoto' como padrão
        ttk.Label(info_frame, text=tipo, font=('Helvetica', 10)).grid(row=0, column=5, sticky=tk.W)


        ttk.Label(fields_frame, text="Cliente:").grid(row=0, column=0, sticky=tk.W)
        cliente_label = ttk.Label(fields_frame, text=atendimento["cliente"])
        cliente_label.grid(row=0, column=1, sticky=tk.W)

        ttk.Label(fields_frame, text="Usuário:").grid(row=1, column=0, sticky=tk.W)
        usuario_label = ttk.Label(fields_frame, text=atendimento.get("usuario", "N/A"))
        usuario_label.grid(row=1, column=1, sticky=tk.W)

        ttk.Label(fields_frame, text="Data Inicial:").grid(row=2, column=0, sticky=tk.W)
        data_inicial = (
            atendimento["eventos"][0]["data"].strftime("%d/%m/%Y")
            if atendimento["eventos"]
            else "N/A"
        )
        data_label = ttk.Label(fields_frame, text=data_inicial)
        data_label.grid(row=2, column=1, sticky=tk.W)

        ttk.Label(fields_frame, text="Hora Inicial:").grid(row=3, column=0, sticky=tk.W)
        hora_inicial = (
            atendimento["eventos"][0]["hora"].strftime("%H:%M")
            if atendimento["eventos"]
            else "N/A"
        )
        hora_label = ttk.Label(fields_frame, text=hora_inicial)
        hora_label.grid(row=3, column=1, sticky=tk.W)


        ttk.Label(fields_frame, text="Problema a resolver:").grid(row=4, column=0, sticky=tk.W)
        problema_entry = scrolledtext.ScrolledText(
            fields_frame,
            width=80,
            height=4,
            wrap=tk.WORD
        )
        problema_entry.grid(row=4, column=1, sticky=tk.W)
        problema_entry.insert(1.0, atendimento.get("problema", ""))
        problema_entry.bind("<<Paste>>", self.colar_texto_com_substituicao)
        problema_entry.config(state=tk.DISABLED)
        # Adiciona menu de contexto
        problema_entry.bind("<Button-3>", lambda e: self.criar_menu_contexto_generico(e, detalhes_window))

        ttk.Label(fields_frame, text="Tarefa realizada:").grid(row=5, column=0, sticky=tk.W)
        tarefa_entry = scrolledtext.ScrolledText(
            fields_frame,
            width=80,
            height=8,
            wrap=tk.WORD
        )
        tarefa_entry.grid(row=5, column=1, sticky=tk.W)
        tarefa_entry.insert(1.0, atendimento.get("tarefa", ""))
        tarefa_entry.bind("<<Paste>>", self.colar_texto_com_substituicao)
        tarefa_entry.config(state=tk.DISABLED)
        # Adiciona menu de contexto
        tarefa_entry.bind("<Button-3>", lambda e: self.criar_menu_contexto_generico(e, detalhes_window))

        ttk.Label(fields_frame, text="Histórico de Eventos:").grid(row=6, column=0, sticky=tk.W)
        eventos_text = scrolledtext.ScrolledText(fields_frame, width=30, height=10)
        eventos_str = "\n".join(
        [
            f"{'Início' if e['tipo'] == 'inicio' else e['tipo'].capitalize()}: {e['data'].strftime('%d/%m/%Y')} {e['hora'].strftime('%H:%M')}"
            for e in atendimento["eventos"]
        ]
        )
        eventos_text.insert(tk.END, eventos_str)
        eventos_text.grid(row=6, column=1, sticky=tk.W)
        eventos_text.config(state=tk.DISABLED)
        # Adiciona menu de contexto
        eventos_text.bind("<Button-3>", lambda e: self.criar_menu_contexto_generico(e, detalhes_window))

        tempo_total = atendimento.get("tempo_total", timedelta())
        if tempo_total:
            horas = int(tempo_total.total_seconds() // 3600)
            minutos = int((tempo_total.total_seconds() % 3600) // 60)
            tempo_str = f"{horas:02d}:{minutos:02d}"
        else:
            tempo_str = "N/A"
        ttk.Label(fields_frame, text="Tempo Total:").grid(row=7, column=0, sticky=tk.W)
        tempo_label = ttk.Label(fields_frame, text=tempo_str)
        tempo_label.grid(row=7, column=1, sticky=tk.W)

        detalhes_window.problema_entry = problema_entry
        detalhes_window.tarefa_entry = tarefa_entry
        detalhes_window.eventos_text = eventos_text
        detalhes_window.original_atendimento = original_atendimento
        detalhes_window.edit_button = edit_button
        detalhes_window.save_button = save_button

        # Configura atalhos para janela
        self.configurar_atalhos_janela(
            detalhes_window,
            [problema_entry, tarefa_entry, eventos_text]
        )

    def toggle_edit(self, window, enable):
        state = tk.NORMAL if enable else tk.DISABLED

        # Verifica e configura cada widget apenas se existir
        if hasattr(window, 'problema_entry'):
            window.problema_entry.config(state=state)
        if hasattr(window, 'tarefa_entry'):
            window.tarefa_entry.config(state=state)
        if hasattr(window, 'eventos_text'):
            window.eventos_text.config(state=state)

        # Configura os botões apenas se existirem
        if hasattr(window, 'edit_button'):
            window.edit_button.config(state=tk.DISABLED if enable else tk.NORMAL)
        if hasattr(window, 'save_button'):
            window.save_button.config(state=tk.NORMAL if enable else tk.DISABLED)

    def salvar_edicao(self, original_atendimento, window):
        """Salva as alterações feitas no atendimento e atualiza o arquivo todos.txt."""
        # Obtém o número do atendimento antes de fazer alterações
        numero_atendimento = getattr(window, 'numero_atendimento', '')

        # Obtém os novos valores dos campos de edição
        new_problema = window.problema_entry.get("1.0", tk.END).strip()
        new_tarefa = window.tarefa_entry.get("1.0", tk.END).strip()
        new_eventos = window.eventos_text.get("1.0", tk.END).strip()

        # Valida o histórico de eventos
        try:
            eventos = self.parse_eventos(new_eventos)
        except ValueError as e:
            mostrar_erro(window, f"Formato inválido no histórico de eventos: {str(e)}")
            return

        # Atualiza o atendimento com os novos valores
        new_atendimento = copy.deepcopy(original_atendimento)
        new_atendimento["problema"] = new_problema
        new_atendimento["tarefa"] = new_tarefa
        new_atendimento["eventos"] = eventos

        # Recalcula o tempo total
        tempo_total = self.calcular_tempo_total_eventos(eventos)
        new_atendimento["tempo_total"] = tempo_total

        # Obtém o bloco original e o novo bloco formatado
        original_block = self.formatar_atendimento(original_atendimento)
        new_block = self.formatar_atendimento(new_atendimento)

        # Obtém o caminho do arquivo todos.txt
        # Obtém o caminho na NOVA estrutura (atendimentos/ano/mês/)
        data_inicio = original_atendimento["eventos"][0]["data"]
        ano_dir = self.atendimentos_dir / str(data_inicio.year)
        mes_dir = ano_dir / data_inicio.strftime("%B").lower()

        # Atualiza todos.txt
        todos_path = mes_dir / "todos.txt"
        if todos_path.exists():
            with open(todos_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_block = self.formatar_atendimento(original_atendimento)
            new_block = self.formatar_atendimento(new_atendimento)
            new_content = content.replace(original_block, new_block)

            with open(todos_path, "w", encoding="utf-8") as f:
                f.write(new_content)

        # Atualiza o arquivo do cliente, se existir
        cliente_path = mes_dir / f"{original_atendimento['cliente']}.txt"
        if cliente_path.exists():
            with open(cliente_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Substitui o bloco original pelo novo bloco
            new_content = content.replace(original_block, new_block)

            # Salva o conteúdo atualizado no arquivo
            with open(cliente_path, "w", encoding="utf-8") as f:
                f.write(new_content)

        # Exibe uma mensagem de sucesso
        mostrar_sucesso(window, "Alterações salvas com sucesso!")

        # Fecha a janela de detalhes
        window.destroy()

        # Recarrega o histórico para refletir as alterações
        self.carregar_historico()

        # Restaura a seleção usando o número do atendimento
        if numero_atendimento:
            self.restaurar_selecao_por_numero(numero_atendimento)

    def restaurar_selecao_por_numero(self, numero_atendimento):
        """Restaura a seleção na treeview com base no número do atendimento"""
        if not numero_atendimento:
            return

        # Procura pelo atendimento com o número correspondente
        for i, atendimento in enumerate(self.current_historico):
            if atendimento.get("numero_atendimento", "") == numero_atendimento:
                # Verifica se o índice é válido na treeview
                children = self.tree.get_children()
                if i < len(children):
                    item = children[i]
                    self.tree.selection_set(item)
                    self.tree.focus(item)
                    self.tree.see(item)
                    return

    def remover_atendimento(self, atendimento, window):
        """
        Remove o atendimento dos arquivos todos.txt e cliente.txt
        e adiciona o atendimento removido ao arquivo desistente.txt.
        A janela de confirmação de remoção fica no topo de todas as outras.
        """
        # Cria uma janela temporária para a confirmação
        temp_window = tk.Toplevel(self.root)
        temp_window.withdraw()  # Esconde a janela temporária
        temp_window.wm_attributes("-topmost", 1)  # Define a janela como sempre no topo

        confirmacao = messagebox.askyesno(
            "Confirmar Remoção",
            "Tem certeza que deseja remover este atendimento?",
            parent=temp_window  # Define a janela pai como a temporária
        )

        temp_window.destroy()  # Fecha a janela temporária após a confirmação

        if not confirmacao:
            return

        # Obtém o caminho do arquivo todos.txt
        data_inicio = atendimento["eventos"][0]["data"]
        ano_dir = self.atendimentos_dir / str(data_inicio.year)
        mes_dir = ano_dir / data_inicio.strftime("%B").lower()

        # Remove de todos.txt
        todos_path = mes_dir / "todos.txt"
        if todos_path.exists():
            with open(todos_path, "r", encoding="utf-8") as f:
                content = f.read()

            original_block = self.formatar_atendimento(atendimento)
            new_content = content.replace(original_block, "")

            with open(todos_path, "w", encoding="utf-8") as f:
                f.write(new_content)

        # Remove do arquivo do cliente
        cliente_path = mes_dir / f"{atendimento['cliente']}.txt"
        if cliente_path.exists():
            with open(cliente_path, "r", encoding="utf-8") as f:
                content = f.read()

            new_content = content.replace(original_block, "")
            with open(cliente_path, "w", encoding="utf-8") as f:
                f.write(new_content)

        # Adiciona ao desistente.txt
        desistente_path = mes_dir / "desistente.txt"
        with open(desistente_path, "a", encoding="utf-8") as f:
            f.write(
                f"Cliente: {atendimento['cliente']}\n"
                f"Usuário: {atendimento.get('usuario', '')}\n"
                f"Problema: {atendimento['problema']}\n"
                f"Tarefa: {atendimento['tarefa']}\n"
                f"Data: {data_inicio.strftime('%d/%m/%Y')}\n"
                f"Tempo: 00:00\n"
                "----------------------------------\n"
            )

        # Fecha a janela de detalhes
        window.destroy()

        # Recarrega o histórico para refletir a remoção
        self.carregar_historico()

        # Exibe uma mensagem de sucesso
        mostrar_sucesso(self.root, "Atendimento removido e adicionado ao arquivo desistente.txt!")

    def parse_eventos(self, eventos_str):
        """
        Converte o texto do histórico de eventos em uma lista de eventos.
        """
        eventos = []
        for line in eventos_str.split("\n"):
            if not line.strip():
                continue  # Ignora linhas vazias

            # Normaliza a linha para minúsculas e remove espaços extras
            line = line.strip().lower()

            # Verifica se a linha começa com um tipo de evento válido (incluindo "início" com acento)
            if any(line.startswith(tipo) for tipo in ["início:", "inicio:", "pausa:", "retomada:", "fim:"]):
                # Divide o tipo do evento e o restante da linha
                partes = line.split(":", 1)  # Divide apenas no primeiro ":"
                if len(partes) < 2:
                    raise ValueError(f"Formato inválido na linha: {line}")

                tipo = partes[0].strip()
                # Padroniza para "inicio" sem acento internamente
                if tipo == "início":
                    tipo = "inicio"
                data_hora = partes[1].strip()

                try:
                    # Divide a data e a hora
                    data_str, hora_str = data_hora.split()
                    data = datetime.strptime(data_str, "%d/%m/%Y").date()
                    hora = datetime.strptime(hora_str, "%H:%M").time()
                    eventos.append({"tipo": tipo, "data": data, "hora": hora})
                except ValueError as e:
                    raise ValueError(f"Formato inválido de data/hora na linha: {line}") from e
            else:
                # Ignora linhas que não são eventos
                continue

        return eventos

    def copiar_dados_atendimento(self, atendimento):
        """Copia os dados do atendimento para a área de transferência"""
        try:
            # Extrai o número do atendimento e o atendente
            numero_completo = atendimento.get('numero_atendimento', 'N/A')
            if ' - ' in numero_completo:
                atendente, numero = numero_completo.split(' - ')
            else:
                atendente = 'N/A'
                numero = numero_completo

            # Obtém o tipo do atendimento
            tipo = atendimento.get('tipo', 'Remoto')

            # Formata os dados do atendimento
            dados_formatados = (
                f"Nº do atendimento: {numero}\n"
                f"Atendente: {atendente}\n"
                f"Tipo: {tipo}\n\n"
                f"Cliente: {atendimento['cliente']}\n"
                f"Usuário: {atendimento.get('usuario', 'N/A')}\n\n"
                f"Data Inicial: {atendimento['eventos'][0]['data'].strftime('%d/%m/%Y') if atendimento['eventos'] else 'N/A'}\n"
                f"Hora Inicial: {atendimento['eventos'][0]['hora'].strftime('%H:%M') if atendimento['eventos'] else 'N/A'}\n\n"
                f"Problema: {atendimento.get('problema', 'N/A')}\n\n"
                f"Tarefa: {atendimento.get('tarefa', 'N/A')}\n\n"
                "Eventos:\n"
            )

            # Adiciona os eventos (mostrando "Início" com acento)
            for evento in atendimento['eventos']:
                tipo_exibicao = "Início" if evento['tipo'] == "inicio" else evento['tipo'].capitalize()
                dados_formatados += (
                    f"- {tipo_exibicao}: "
                    f"{evento['data'].strftime('%d/%m/%Y')} {evento['hora'].strftime('%H:%M')}\n"
                )

            # Adiciona o tempo total
            tempo_total = atendimento.get('tempo_total', timedelta())
            if tempo_total:
                horas = int(tempo_total.total_seconds() // 3600)
                minutos = int((tempo_total.total_seconds() % 3600) // 60)
                dados_formatados += f"\nTempo Total: {horas:02d}:{minutos:02d}\n"
            else:
                dados_formatados += "\nTempo Total: N/A\n"

            # Copia para a área de transferência
            self.root.clipboard_clear()
            self.root.clipboard_append(dados_formatados)
            self.root.update()  # Mantém o conteúdo na área de transferência após o programa fechar

            return True
        except Exception as e:
            print(f"Erro ao copiar dados do atendimento: {e}")
            return False

    def verificar_status_botao(self, atendimento):
        """Verifica o status do atendimento e configura o botão apropriadamente"""
        if hasattr(self, 'status_btn'):
            # Obtém o número do atendimento (apenas a parte numérica)
            numero_atendimento_completo = atendimento.get('numero_atendimento', '')
            numero_atendimento = numero_atendimento_completo.split(' - ')[-1]

            if not numero_atendimento:
                self.status_btn.config(text="Status desconhecido", style="")
                return

            # Verifica o status no arquivo status.txt
            data_inicio = atendimento["eventos"][0]["data"]
            ano_dir = self.atendimentos_dir / str(data_inicio.year)
            mes_dir = ano_dir / data_inicio.strftime("%B").lower()
            status_path = mes_dir / "status.txt"

            if status_path.exists():
                with open(status_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Divide o conteúdo em blocos de atendimento
                blocos = content.split("**********************************\n")

                for bloco in blocos:
                    if f"Número do atendimento: {numero_atendimento}" in bloco:
                        if "Situação: Processado" in bloco:
                            self.status_btn.config(text="Processado", style="Green.TButton")
                            return
                        elif "Situação: Não Processado" in bloco:
                            self.status_btn.config(text="Não Processado", style="Red.TButton")
                            return

            # Se não encontrou o atendimento ou o status, define como não processado
            self.status_btn.config(text="Não Processado", style="Red.TButton")

    def alternar_status_atendimento(self, window, atendimento):
        """Alterna o status entre Processado e Não Processado"""
        # Obtém o número do atendimento (apenas a parte numérica)
        numero_atendimento_completo = atendimento.get('numero_atendimento', '')
        numero_atendimento = numero_atendimento_completo.split(' - ')[-1]

        if not numero_atendimento:
            mostrar_erro(window, "Não foi possível identificar o número do atendimento.")
            return

        # Obtém o caminho do arquivo status.txt
        data_inicio = atendimento["eventos"][0]["data"]
        ano_dir = self.atendimentos_dir / str(data_inicio.year)
        mes_dir = ano_dir / data_inicio.strftime("%B").lower()
        status_path = mes_dir / "status.txt"

        if not status_path.exists():
            mostrar_erro(window, "Arquivo de status não encontrado.")
            return

        # Lê o conteúdo do arquivo
        with open(status_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Divide o conteúdo em blocos de atendimento
        blocos = content.split("**********************************\n")
        novo_conteudo = []
        status_alterado = False

        for bloco in blocos:
            if not bloco.strip():
                continue

            if f"Número do atendimento: {numero_atendimento}" in bloco:
                # Este é o bloco do atendimento que queremos alterar
                linhas = bloco.split('\n')
                novo_bloco = []

                for linha in linhas:
                    if linha.startswith("Situação: "):
                        # Altera o status mantendo o mesmo formato
                        if "Não Processado" in linha:
                            novo_bloco.append("Situação: Processado")
                        elif "Processado" in linha:
                            novo_bloco.append("Situação: Não Processado")
                        else:
                            novo_bloco.append("Situação: Não Processado")
                    else:
                        novo_bloco.append(linha)

                # Junta as linhas mantendo as quebras de linha originais
                novo_bloco = '\n'.join(novo_bloco)

                # Atualiza o botão
                if "Situação: Processado" in novo_bloco:
                    self.status_btn.config(text="Processado", style="Green.TButton")
                else:
                    self.status_btn.config(text="Não Processado", style="Red.TButton")

                novo_conteudo.append(novo_bloco)
                status_alterado = True
            else:
                novo_conteudo.append(bloco)

        if status_alterado:
            # Reconstrói o conteúdo do arquivo mantendo o formato original
            novo_conteudo_completo = "**********************************\n".join(novo_conteudo)

            # Garante que termina com a linha de separação, mas sem quebras extras
            novo_conteudo_completo = novo_conteudo_completo.strip()
            novo_conteudo_completo += "\n**********************************\n"

            # Salva o arquivo com o novo status
            with open(status_path, "w", encoding="utf-8") as f:
                f.write(novo_conteudo_completo)

            # Obtém o novo status do botão para exibir a mensagem correta
            novo_status = self.status_btn.cget("text")
            mostrar_sucesso(window, f"Status alterado para {novo_status} com sucesso!")
        else:
            mostrar_erro(window, "Atendimento não encontrado no arquivo de status.")

    def abrir_detalhes_selecionado(self):
        """Abre a janela de detalhes para o item selecionado no histórico"""
        selecionados = self.tree.selection()
        if not selecionados:
            messagebox.showwarning("Aviso", "Selecione um atendimento para visualizar os detalhes.")
            return

        # Simula um evento de duplo clique para reutilizar a função existente
        event = type('Evento', (), {'widget': self.tree})()
        self.visualizar_detalhes(event)

    def calcular_tempo_total_eventos(self, eventos):
        """
        Calcula o tempo total com base nos eventos.
        """
        tempo_total = timedelta()
        inicio = None

        for evento in eventos:
            dt = datetime.combine(evento["data"], evento["hora"])
            if evento["tipo"] == "inicio":
                inicio = dt
            elif evento["tipo"] == "pausa" and inicio:
                tempo_total += dt - inicio
                inicio = None
            elif evento["tipo"] == "retomada":
                inicio = dt
            elif evento["tipo"] == "fim" and inicio:
                tempo_total += dt - inicio
                inicio = None

        return tempo_total

    def update_file(self, file_path, original_block, new_block):
        if not file_path.exists():
            return

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        blocks = content.split("**********************************\n")
        new_blocks = []
        for block in blocks:
            if block.strip() == original_block.strip():
                new_blocks.append(new_block.strip())
            else:
                new_blocks.append(block.strip())

        new_content = "**********************************\n".join(new_blocks)
        if content.endswith("**********************************\n"):
            new_content += "\n**********************************\n"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

    def criar_janela_espelhamentos(self):
        """
        Cria uma nova janela para exibir os snapshots de espelhamento.
        """
        # Verifica se a janela já existe e está aberta
        if hasattr(self, 'janela_espelhamentos') and self.janela_espelhamentos is not None and self.janela_espelhamentos.winfo_exists():
            # Se a janela já existe, traz para frente
            self.janela_espelhamentos.lift()
            self.janela_espelhamentos.focus_force()
            return

        # Obtém o cliente e usuário atualmente selecionados
        cliente = self.cliente_var.get().strip()
        usuario = self.usuario_var.get().strip()

        if not cliente or not usuario:
            mostrar_erro(self.root, "Selecione um cliente e usuário antes de abrir os espelhamentos.")
            return

        try:
            self.janela_espelhamentos = tk.Toplevel(self.root)
            self.janela_espelhamentos.title(f"Espelhamentos - {cliente} - {usuario}")
            self.janela_espelhamentos.geometry("800x600")

            # Configura para fechar corretamente a janela
            self.janela_espelhamentos.protocol("WM_DELETE_WINDOW", self.fechar_janela_espelhamentos)

            # Frame principal
            main_frame = ttk.Frame(self.janela_espelhamentos)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Frame para a lista de snapshots
            lista_frame = ttk.Frame(main_frame)
            lista_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

            # Lista de snapshots
            ttk.Label(lista_frame, text="Snapshots:").pack()
            self.lista_snapshots = tk.Listbox(lista_frame, width=30, height=20)
            self.lista_snapshots.pack(fill=tk.Y, expand=True)
            self.lista_snapshots.bind("<<ListboxSelect>>", self.carregar_snapshot_selecionado)

            # Frame para os botões de ação
            botoes_frame = ttk.Frame(lista_frame)
            botoes_frame.pack(fill=tk.X, pady=5)

            # Botão para remover snapshot
            ttk.Button(botoes_frame, text="Remover Snapshot",
                    command=self.remover_snapshot_selecionado).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)

            # Frame para o conteúdo do snapshot
            conteudo_frame = ttk.Frame(main_frame)
            conteudo_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

            # Área de texto para exibir o conteúdo do snapshot
            ttk.Label(conteudo_frame, text="Conteúdo do Snapshot:").pack()
            self.snapshot_text = scrolledtext.ScrolledText(conteudo_frame, wrap=tk.WORD, state=tk.DISABLED)
            self.snapshot_text.pack(fill=tk.BOTH, expand=True)

            # Adiciona o menu de contexto ao texto de snapshot
            self.snapshot_text.bind("<Button-3>", lambda e: self.criar_menu_contexto_generico(e, self.janela_espelhamentos))

            # Botão para copiar o conteúdo
            ttk.Button(conteudo_frame, text="Copiar Conteúdo", command=self.copiar_conteudo_snapshot).pack(pady=5)

            # Carregar os snapshots disponíveis para o cliente e usuário atuais
            self.carregar_snapshots(cliente, usuario)

            # Configura atalhos para esta janela
            self.configurar_atalhos_janela(
                self.janela_espelhamentos,
                [self.snapshot_text]
            )

        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro ao abrir os espelhamentos:\n{str(e)}")
            print(f"Erro detalhado: {traceback.format_exc()}")
            if hasattr(self, 'janela_espelhamentos') and self.janela_espelhamentos is not None:
                self.janela_espelhamentos.destroy()
                self.janela_espelhamentos = None

    def remover_snapshot_selecionado(self):
        """
        Remove o snapshot selecionado do arquivo cliente-usuario.old e renumerar os snapshots restantes.
        """
        # Obtém o cliente e usuário atuais
        cliente = self.cliente_var.get().strip()
        usuario = self.usuario_var.get().strip()

        if not cliente or not usuario:
            mostrar_erro(self.root, "Selecione um cliente e usuário antes de remover snapshots.")
            return

        # Verifica se há um snapshot selecionado
        selecionado = self.lista_snapshots.curselection()
        if not selecionado:
            mostrar_erro(self.root, "Selecione um snapshot para remover.")
            return

        # Confirmação do usuário
        confirmacao = messagebox.askyesno(
            "Confirmar Remoção",
            "Tem certeza que deseja remover este snapshot? Esta ação não pode ser desfeita.",
            parent=self.janela_espelhamentos
        )

        if not confirmacao:
            return

        # Nome do arquivo de snapshots
        nome_arquivo = f"{cliente}-{usuario}.old".replace("/", "_")
        arquivo_snapshot = self.dados_usuario_dir / nome_arquivo

        if not arquivo_snapshot.exists():
            mostrar_erro(self.root, f"Nenhum espelhamento encontrado para {cliente} - {usuario}.")
            return

        # Lê todos os snapshots do arquivo
        with open(arquivo_snapshot, "r", encoding="utf-8") as f:
            conteudo = f.read()

        # Divide o conteúdo em snapshots individuais
        snapshots = conteudo.split("***********************************\n")
        snapshots = [s.strip() for s in snapshots if s.strip()]

        # Remove o snapshot selecionado
        indice_selecionado = selecionado[0]
        if 0 <= indice_selecionado < len(snapshots):
            snapshots.pop(indice_selecionado)
        else:
            mostrar_erro(self.root, "Índice de snapshot inválido.")
            return

        # Renumera os snapshots restantes em sequência crescente
        novos_snapshots = []
        for i, snapshot in enumerate(snapshots, 1):
            # Atualiza o número do espelhamento
            if snapshot.startswith("Espelhamento:"):
                linhas = snapshot.split("\n")
                # Atualiza a linha do espelhamento
                linhas[0] = f"Espelhamento: {i}"
                snapshot = "\n".join(linhas)
            novos_snapshots.append(snapshot)

        # Reconstrói o conteúdo do arquivo
        novo_conteudo = "\n***********************************\n".join(novos_snapshots)
        if novo_conteudo:
            novo_conteudo += "\n***********************************\n"

        # Salva o arquivo atualizado
        with open(arquivo_snapshot, "w", encoding="utf-8") as f:
            f.write(novo_conteudo)

        # Recarrega a lista de snapshots
        self.carregar_snapshots(cliente, usuario)

        # Limpa o conteúdo exibido
        self.snapshot_text.config(state=tk.NORMAL)
        self.snapshot_text.delete("1.0", tk.END)
        self.snapshot_text.config(state=tk.DISABLED)

        mostrar_sucesso(self.janela_espelhamentos, "Snapshot removido com sucesso e os demais foram renumerados!")

    def fechar_janela_espelhamentos(self):
        """Fecha a janela de espelhamentos corretamente"""
        if hasattr(self, 'janela_espelhamentos') and self.janela_espelhamentos is not None:
            self.janela_espelhamentos.destroy()
            self.janela_espelhamentos = None

    def criar_janela_anotacoes(self):
        """
        Cria uma janela para anotações com funcionalidades de edição, desfazer/refazer,
        marcação de cores persistentes, formatação de texto e salva automaticamente em notas.txt.
        """
        # Verifica se a janela já existe e está aberta
        if hasattr(self, 'janela_anotacoes') and self.janela_anotacoes is not None and self.janela_anotacoes.winfo_exists():
            # Se a janela já existe, traz para frente
            self.janela_anotacoes.lift()
            self.janela_anotacoes.focus_force()
            return

        try:
            # Inicializa variáveis se não existirem
            if not hasattr(self, 'historico_anotacoes'):
                self.historico_anotacoes = []
                self.indice_historico = -1
                self.ignorar_evento = False

            self.janela_anotacoes = tk.Toplevel(self.root)
            self.janela_anotacoes.title("Anotações")
            self.janela_anotacoes.geometry("780x560")

            # Configura para fechar corretamente a janela
            self.janela_anotacoes.protocol("WM_DELETE_WINDOW", lambda: self.fechar_janela_anotacoes())

            # Frame principal
            main_frame = ttk.Frame(self.janela_anotacoes)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Frame de ferramentas
            tools_frame = ttk.Frame(main_frame)
            tools_frame.pack(fill=tk.X, pady=5)

            # Botões de desfazer/refazer
            ttk.Button(tools_frame, text="Desfazer", command=lambda: self.desfazer_anotacao()).pack(side=tk.LEFT, padx=2)
            ttk.Button(tools_frame, text="Refazer", command=lambda: self.refazer_anotacao()).pack(side=tk.LEFT, padx=2)

            # Botões de formatação de texto
            format_frame = ttk.Frame(tools_frame)
            format_frame.pack(side=tk.LEFT, padx=5)

            # Botão Negrito
            self.bold_btn = ttk.Button(format_frame, text="Negrito", style="Bold.TButton",
                                    command=lambda: self.aplicar_formato_texto("bold"))
            self.bold_btn.pack(side=tk.LEFT, padx=2)

            # Botão Sublinhado
            self.underline_btn = ttk.Button(format_frame, text="Sublinhado", style="Underline.TButton",
                                        command=lambda: self.aplicar_formato_texto("underline"))
            self.underline_btn.pack(side=tk.LEFT, padx=2)

            # Botões de cor
            colors_frame = ttk.Frame(tools_frame)
            colors_frame.pack(side=tk.LEFT, padx=5)

            ttk.Label(colors_frame, text="Cores:").pack(side=tk.LEFT)
            ttk.Button(colors_frame, text="Amarelo", command=lambda: self.aplicar_cor_anotacao("yellow")).pack(side=tk.LEFT, padx=2)
            ttk.Button(colors_frame, text="Verde", command=lambda: self.aplicar_cor_anotacao("lightgreen")).pack(side=tk.LEFT, padx=2)
            ttk.Button(colors_frame, text="Azul", command=lambda: self.aplicar_cor_anotacao("lightblue")).pack(side=tk.LEFT, padx=2)
            ttk.Button(colors_frame, text="Vermelho", command=lambda: self.aplicar_cor_anotacao("salmon")).pack(side=tk.LEFT, padx=2)
            ttk.Button(colors_frame, text="Normal", command=lambda: self.aplicar_cor_anotacao("white")).pack(side=tk.LEFT, padx=2)

            # Área de texto para anotações
            self.anotacoes_text = scrolledtext.ScrolledText(
                main_frame,
                wrap=tk.WORD,
                undo=True,
                maxundo=-1
            )
            self.anotacoes_text.pack(fill=tk.BOTH, expand=True)

            # Adiciona o binding para colar com substituição
            self.anotacoes_text.bind("<<Paste>>", self.colar_texto_com_substituicao)

            # Configura tags para cores e formatação
            self.cores_disponiveis = {
                "yellow": "Amarelo",
                "lightgreen": "Verde",
                "lightblue": "Azul",
                "salmon": "Vermelho",
                "white": "Normal"
            }

            # Configura estilo para os botões de formatação
            style = ttk.Style()
            style.configure("Bold.TButton", font=('Helvetica', 10, 'bold'))
            style.configure("Underline.TButton", font=('Helvetica', 10, 'underline'))

            # Configura tags para formatação de texto que podem ser combinadas
            self.anotacoes_text.tag_config("bold", font=('Liberation Serif', 12, 'bold'))
            self.anotacoes_text.tag_config("underline", font=('Liberation Serif', 12, 'underline'))

            # Configura uma tag combinada para negrito e sublinhado
            self.anotacoes_text.tag_config("bold_underline",
                                        font=('Liberation Serif', 12, 'bold underline'))

            for color in self.cores_disponiveis:
                self.anotacoes_text.tag_config(color, background=color)

            # Adiciona o menu de contexto específico para anotações
            self.anotacoes_text.bind("<Button-3>", self.criar_menu_contexto_anotacoes)

            # Caminho do arquivo de anotações
            self.anotacoes_file = self.base_dir / "notas.txt"
            self.anotacoes_tags_file = self.config_dir / "notas_tags.json"

            # Carrega as anotações existentes
            self.carregar_anotacoes()

            # Configura o salvamento automático
            self.anotacoes_text.bind("<KeyRelease>", self.salvar_anotacoes)
            self.anotacoes_text.bind("<<Modified>>", lambda e: self.anotacoes_text.edit_modified(False))

            # Configura atalhos para esta janela
            self.configurar_atalhos_janela(
                self.janela_anotacoes,
                [self.anotacoes_text]
            )

        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro ao abrir as anotações:\n{str(e)}")
            print(f"Erro detalhado: {traceback.format_exc()}")

    def aplicar_formato_texto(self, formato):
        """Aplica formatação de texto (negrito/sublinhado) à seleção ou texto a ser digitado"""
        try:
            if self.anotacoes_text.tag_ranges(tk.SEL):
                start = self.anotacoes_text.index(tk.SEL_FIRST)
                end = self.anotacoes_text.index(tk.SEL_LAST)

                # Obtém tags atuais
                current_tags = set(self.anotacoes_text.tag_names(start))

                # Determina o novo conjunto de tags
                new_tags = current_tags.copy()
                if formato in current_tags:
                    new_tags.remove(formato)
                else:
                    new_tags.add(formato)

                # Remove todas as tags de formatação primeiro
                for tag in ["bold", "underline", "bold_underline"]:
                    self.anotacoes_text.tag_remove(tag, start, end)

                # Aplica as novas tags
                if "bold" in new_tags and "underline" in new_tags:
                    self.anotacoes_text.tag_add("bold_underline", start, end)
                elif "bold" in new_tags:
                    self.anotacoes_text.tag_add("bold", start, end)
                elif "underline" in new_tags:
                    self.anotacoes_text.tag_add("underline", start, end)
            else:
                # Para texto a ser digitado - configura uma marca para aplicar a formatação
                insert_pos = self.anotacoes_text.index(tk.INSERT)
                self.anotacoes_text.mark_set("format_start", insert_pos)

                # Configura a tag para o formato especificado
                if formato == "bold":
                    self.anotacoes_text.tag_config(formato, font=('Liberation Serif', 11, 'bold'))
                elif formato == "underline":
                    self.anotacoes_text.tag_config(formato, font=('Liberation Serif', 11, 'underline'))

                # Vincula o evento de tecla para aplicar a formatação
                self.anotacoes_text.bind("<Key>",
                                    lambda e: self.aplicar_formato_digitacao(e, formato),
                                    add='+')
        except Exception as e:
            print(f"Erro ao aplicar formatação: {e}")

    def aplicar_formato_digitacao(self, event, formato):
        """Aplica formatação ao texto que está sendo digitado"""
        try:
            if event.keysym not in ['BackSpace', 'Delete', 'Left', 'Right', 'Up', 'Down']:
                # Obtém a posição inicial
                start = self.anotacoes_text.index("format_start")
                end = self.anotacoes_text.index(tk.INSERT)

                # Verifica se há outras tags aplicadas no intervalo
                current_tags = set()
                for tag in self.anotacoes_text.tag_names():
                    if tag in ["bold", "underline"] and self.anotacoes_text.tag_ranges(tag):
                        ranges = self.anotacoes_text.tag_ranges(tag)
                        for i in range(0, len(ranges), 2):
                            tag_start = self.anotacoes_text.index(ranges[i])
                            tag_end = self.anotacoes_text.index(ranges[i+1])
                            if (self.anotacoes_text.compare(start, '>=', tag_start) and
                                self.anotacoes_text.compare(end, '<=', tag_end)):
                                current_tags.add(tag)

                # Aplica a tag ao intervalo
                self.anotacoes_text.tag_add(formato, start, end)

                # Mantém outras formatações existentes
                for tag in current_tags:
                    if tag != formato:
                        self.anotacoes_text.tag_add(tag, start, end)

                # Se o usuário mover o cursor, remove o binding para não aplicar a formatação
                if event.keysym in ['Left', 'Right', 'Up', 'Down']:
                    self.anotacoes_text.unbind("<Key>")
        except Exception as e:
            print(f"Erro ao aplicar formatação durante digitação: {e}")
            self.anotacoes_text.unbind("<Key>")

    def fechar_janela_anotacoes(self):
        """Salva as anotações antes de fechar a janela"""
        if hasattr(self, 'janela_anotacoes') and self.janela_anotacoes is not None:
            if hasattr(self, 'anotacoes_text') and self.anotacoes_text is not None:
                self.salvar_anotacoes()
            self.janela_anotacoes.destroy()
            self.janela_anotacoes = None

    def carregar_anotacoes(self):
        """Carrega o texto e todas as formatações (cores, negrito, sublinhado)"""
        try:
            # Configura o estado inicial como vazio
            estado = {'texto': '', 'tags': {}}

            # Carrega o texto se o arquivo existir
            if self.anotacoes_file.exists():
                with open(self.anotacoes_file, "r", encoding="utf-8") as f:
                    estado['texto'] = f.read()

            # Carrega as tags se o arquivo existir
            if self.anotacoes_tags_file.exists():
                try:
                    with open(self.anotacoes_tags_file, "r", encoding="utf-8") as f:
                        estado['tags'] = json.load(f)
                except (json.JSONDecodeError, Exception) as e:
                    print(f"Erro ao carregar tags: {e}")
                    estado['tags'] = {}

            # Aplica o estado carregado
            self.aplicar_estado_completo(estado)

            # Adiciona ao histórico
            self.adicionar_ao_historico(estado)

        except Exception as e:
            print(f"Erro ao carregar anotações: {e}")

    def validar_posicao(self, pos):
        """Verifica se uma posição é válida no texto"""
        try:
            # Tenta converter a posição para índices linha/coluna
            linha, col = map(int, pos.split('.'))
            return linha > 0 and col >= 0
        except:
            return False

    def salvar_anotacoes(self, event=None):
        """Salva o texto e todas as formatações (cores, negrito, sublinhado)"""
        if not hasattr(self, 'ignorar_evento') or not self.ignorar_evento:
            if hasattr(self, 'anotacoes_text') and self.anotacoes_text is not None:
                try:
                    # Obtém o estado completo (texto + todas as tags)
                    estado = self.obter_estado_completo()

                    # Salva o texto
                    with open(self.anotacoes_file, "w", encoding="utf-8") as f:
                        f.write(estado['texto'])

                    # Prepara as tags para salvar (incluindo negrito e sublinhado)
                    tags_para_salvar = {}
                    for tag in self.anotacoes_text.tag_names():
                        if tag == "sel":
                            continue  # Ignora a tag de seleção padrão

                        ranges = self.anotacoes_text.tag_ranges(tag)
                        tags_para_salvar[tag] = [
                            (self.anotacoes_text.index(ranges[i]),
                            self.anotacoes_text.index(ranges[i+1]))
                            for i in range(0, len(ranges), 2)
                        ]

                    # Salva as tags em formato JSON
                    with open(self.anotacoes_tags_file, "w", encoding="utf-8") as f:
                        json.dump(tags_para_salvar, f, indent=2)

                    # Adiciona ao histórico
                    self.adicionar_ao_historico(estado)

                except Exception as e:
                    print(f"Erro ao salvar anotações: {e}")

    def adicionar_ao_historico(self, conteudo=None):
        """Adiciona o estado atual ao histórico de anotações"""
        # Se não for fornecido conteúdo, obtém o estado atual
        estado = self.obter_estado_completo() if conteudo is None else conteudo

        # Remove estados futuros se estamos no meio do histórico
        if self.indice_historico < len(self.historico_anotacoes) - 1:
            self.historico_anotacoes = self.historico_anotacoes[:self.indice_historico + 1]

        # Adiciona o novo estado
        self.historico_anotacoes.append(estado)
        self.indice_historico = len(self.historico_anotacoes) - 1

        # Limita o histórico a 100 estados
        if len(self.historico_anotacoes) > 100:
            self.historico_anotacoes.pop(0)
            self.indice_historico -= 1

    def desfazer_anotacao(self):
        """Desfaz a última alteração mantendo todas as formatações"""
        if self.indice_historico > 0:
            # Salva o estado atual antes de desfazer
            estado_atual = self.obter_estado_completo()

            # Move para o estado anterior
            self.indice_historico -= 1
            estado_anterior = self.historico_anotacoes[self.indice_historico]

            # Aplica o estado anterior
            self.aplicar_estado_completo(estado_anterior)

            # Atualiza o histórico se necessário
            if len(self.historico_anotacoes) > self.indice_historico + 1:
                self.historico_anotacoes[self.indice_historico + 1] = estado_atual
            else:
                self.historico_anotacoes.append(estado_atual)

    def refazer_anotacao(self):
        """Refaz a última alteração desfeita mantendo todas as formatações"""
        if self.indice_historico < len(self.historico_anotacoes) - 1:
            # Salva o estado atual antes de refazer
            estado_atual = self.obter_estado_completo()

            # Move para o estado posterior
            self.indice_historico += 1
            estado_posterior = self.historico_anotacoes[self.indice_historico]

            # Aplica o estado posterior
            self.aplicar_estado_completo(estado_posterior)

            # Atualiza o histórico se necessário
            if self.indice_historico > 0:
                self.historico_anotacoes[self.indice_historico - 1] = estado_atual

    def obter_estado_completo(self):
        """Obtém o estado completo do texto (conteúdo + formatações)"""
        estado = {
            'texto': self.anotacoes_text.get("1.0", tk.END),
            'tags': {}
        }

        # Captura todas as tags e suas posições
        for tag in self.anotacoes_text.tag_names():
            if tag != "sel":  # Ignora a tag de seleção padrão
                ranges = self.anotacoes_text.tag_ranges(tag)
                estado['tags'][tag] = [
                    (self.anotacoes_text.index(ranges[i]),
                    self.anotacoes_text.index(ranges[i+1]))
                    for i in range(0, len(ranges), 2)
                ]

        return estado

    def aplicar_estado_completo(self, estado):
        """Aplica um estado completo ao widget de texto (texto + formatações)"""
        self.ignorar_evento = True

        try:
            # Limpa o texto atual e todas as tags
            self.anotacoes_text.delete("1.0", tk.END)
            for tag in self.anotacoes_text.tag_names():
                if tag != "sel":  # Não remove a tag de seleção padrão
                    self.anotacoes_text.tag_remove(tag, "1.0", tk.END)

            # Insere o novo texto
            self.anotacoes_text.insert("1.0", estado['texto'])

            # Aplica todas as tags do estado
            for tag, ranges in estado['tags'].items():
                # Configura a tag se não existir
                if tag not in self.anotacoes_text.tag_names():
                    if tag in self.cores_disponiveis:
                        self.anotacoes_text.tag_config(tag, background=tag)
                    elif tag == "bold":
                        self.anotacoes_text.tag_config(tag, font=('Liberation Serif', 11, 'bold'))
                    elif tag == "underline":
                        self.anotacoes_text.tag_config(tag, font=('Liberation Serif', 11, 'underline'))

                # Aplica a tag aos intervalos especificados
                for start, end in ranges:
                    try:
                        if self.validar_posicao(start) and self.validar_posicao(end):
                            self.anotacoes_text.tag_add(tag, start, end)
                    except Exception as e:
                        print(f"Erro ao aplicar tag {tag} de {start} a {end}: {e}")
                        continue

        finally:
            self.ignorar_evento = False

    def obter_todas_marcacoes(self):
        """Obtém todas as marcações (cores e formatação) atuais"""
        marcacoes = {}
        for tag in self.anotacoes_text.tag_names():
            ranges = self.anotacoes_text.tag_ranges(tag)
            marcacoes[tag] = [(self.anotacoes_text.index(ranges[i]),
                            self.anotacoes_text.index(ranges[i+1]))
                            for i in range(0, len(ranges), 2)]
        return marcacoes

    def restaurar_todas_marcacoes(self, marcacoes):
        """Restaura todas as marcações (cores e formatação) salvas"""
        # Primeiro remove todas as marcações existentes
        for tag in self.anotacoes_text.tag_names():
            if tag != "sel":  # Não remove a tag de seleção padrão
                self.anotacoes_text.tag_remove(tag, "1.0", tk.END)

        # Depois aplica as marcações salvas
        for tag, ranges in marcacoes.items():
            if tag != "sel":  # Não restaura a tag de seleção padrão
                for start, end in ranges:
                    try:
                        if self.validar_posicao(start) and self.validar_posicao(end):
                            self.anotacoes_text.tag_add(tag, start, end)
                    except:
                        continue


    def obter_marcacoes_cores(self):
        """Obtém todas as marcações de cores atuais"""
        marcacoes = {}
        for tag in self.cores_disponiveis:
            ranges = self.anotacoes_text.tag_ranges(tag)
            marcacoes[tag] = [(self.anotacoes_text.index(ranges[i]),
                            self.anotacoes_text.index(ranges[i+1]))
                            for i in range(0, len(ranges), 2)]
        return marcacoes

    def restaurar_marcacoes_cores(self, marcacoes):
        """Restaura as marcações de cores salvas"""
        # Primeiro remove todas as marcações existentes
        for tag in self.cores_disponiveis:
            self.anotacoes_text.tag_remove(tag, "1.0", tk.END)

        # Depois aplica as marcações salvas
        for tag, ranges in marcacoes.items():
            for start, end in ranges:
                try:
                    if self.validar_posicao(start) and self.validar_posicao(end):
                        self.anotacoes_text.tag_add(tag, start, end)
                except:
                    continue

    def aplicar_cor_anotacao(self, cor):
        """Aplica a cor selecionada ao texto destacado"""
        try:
            # Remove todas as tags de cor da seleção primeiro
            for tag in self.cores_disponiveis:
                if tag != "white":  # Não remove a tag "normal"
                    if self.anotacoes_text.tag_ranges(tk.SEL):
                        self.anotacoes_text.tag_remove(tag, tk.SEL_FIRST, tk.SEL_LAST)

            # Se não for "Normal", aplica a nova cor
            if cor != "white":
                if self.anotacoes_text.tag_ranges(tk.SEL):
                    self.anotacoes_text.tag_add(cor, tk.SEL_FIRST, tk.SEL_LAST)
                else:
                    # Aplica à linha atual se nada estiver selecionado
                    linha_atual = self.anotacoes_text.index(tk.INSERT).split('.')[0]
                    inicio = f"{linha_atual}.0"
                    fim = f"{linha_atual}.end"
                    self.anotacoes_text.tag_add(cor, inicio, fim)
        except Exception as e:
            print(f"Erro ao aplicar cor: {e}")

    def carregar_snapshots(self, cliente, usuario):
        """
        Carrega os snapshots disponíveis na lista para o cliente e usuário especificados.
        """
        self.lista_snapshots.delete(0, tk.END)
        self.snapshots = []

        nome_arquivo = f"{cliente}-{usuario}.old".replace("/", "_")
        arquivo_snapshot = self.dados_usuario_dir / nome_arquivo

        if not arquivo_snapshot.exists():
            mostrar_erro(self.root, f"Nenhum espelhamento encontrado para {cliente} - {usuario}.")
            return

        try:
            with open(arquivo_snapshot, "r", encoding="utf-8") as f:
                conteudo = f.read()

            # Divide o conteúdo em snapshots individuais usando o delimitador correto
            snapshots = conteudo.split("***********************************\n")
            snapshots = [s.strip() for s in snapshots if s.strip()]

            for i, snapshot in enumerate(snapshots, 1):
                try:
                    # Tenta extrair informações do cabeçalho do snapshot
                    linhas = snapshot.split("\n")
                    if len(linhas) < 3:
                        continue  # Ignora snapshots mal formatados

                    # Verifica o formato do snapshot
                    if linhas[0].startswith("Espelhamento:"):
                        # Formato novo: "Espelhamento: X"
                        num = linhas[0].split(":")[1].strip()
                        data = linhas[1].replace("Data:", "").strip() if linhas[1].startswith("Data:") else "Data desconhecida"
                        hora = linhas[2].replace("Hora:", "").strip() if linhas[2].startswith("Hora:") else "Hora desconhecida"
                    elif "“Temporário”" in linhas[0]:
                        # Formato antigo (para compatibilidade)
                        partes = linhas[0].split("”")
                        if len(partes) >= 4:
                            num = partes[1].replace("“", "").strip()
                            data = partes[2].replace("“data: ", "").strip()
                            hora = partes[3].replace("“Hora:", "").strip()
                        else:
                            num = str(i)
                            data = "Data desconhecida"
                            hora = "Hora desconhecida"
                    else:
                        # Formato desconhecido - usa numeração automática
                        num = str(i)
                        data = "Data desconhecida"
                        hora = "Hora desconhecida"

                    data_hora = f"Espelhamento {num} - {data} {hora}"
                    self.snapshots.append((data_hora, snapshot))
                    self.lista_snapshots.insert(tk.END, data_hora)

                except Exception as e:
                    print(f"Erro ao processar snapshot {i}: {e}")
                    continue

            # Ordena por número de espelhamento (decrescente)
            try:
                self.snapshots.sort(reverse=True, key=lambda x: int(x[0].split()[1]))
            except:
                # Se não conseguir ordenar por número, ordena alfabeticamente
                self.snapshots.sort(reverse=True)

        except Exception as e:
            mostrar_erro(self.root, f"Erro ao ler arquivo de snapshots: {str(e)}")
            print(f"Erro detalhado: {traceback.format_exc()}")

    def parse_snapshot_date(self, date_str):
        """
        Tenta converter a string de data/hora do snapshot em um objeto datetime para ordenação.
        """
        try:
            if "Hora:" in date_str:
                # Formato: "dd/mm/YYYY Hora: HH:MM"
                date_part, time_part = date_str.split("Hora:")
                date_part = date_part.strip()
                time_part = time_part.strip()

                # Remove possíveis espaços extras entre horas e minutos
                time_part = time_part.replace(" ", "")
                if ":" not in time_part and len(time_part) == 4:
                    time_part = f"{time_part[:2]}:{time_part[2:]}"

                return datetime.strptime(f"{date_part} {time_part}", "%d/%m/%Y %H:%M")
            elif "data:" in date_str:
                # Formato antigo: "data: dd/mm/YYYY” “Hora:HHMM"
                parts = date_str.split("”")
                date_part = parts[0].replace("“data: ", "").strip()
                time_part = parts[1].replace("“Hora:", "").strip()

                # Formata a hora para HH:MM se estiver no formato HHMM
                if len(time_part) == 4 and time_part.isdigit():
                    time_part = f"{time_part[:2]}:{time_part[2:]}"

                return datetime.strptime(f"{date_part} {time_part}", "%d/%m/%Y %H:%M")
        except Exception as e:
            print(f"Erro ao parsear data do snapshot: {date_str} - {e}")
            return datetime.min  # Retorna data mínima se não conseguir parsear

    def carregar_snapshot_selecionado(self, event=None):
        """
        Carrega o conteúdo do espelhamento selecionado na área de texto.
        """
        selecionado = self.lista_snapshots.curselection()
        if not selecionado:
            return

        data_hora = self.lista_snapshots.get(selecionado[0])
        snapshot = next((snap[1] for snap in self.snapshots if snap[0] == data_hora), None)

        if snapshot:
            self.snapshot_text.config(state=tk.NORMAL)
            self.snapshot_text.delete("1.0", tk.END)

            # Processa o conteúdo para formatar corretamente
            lines = snapshot.split('\n')
            formatted_lines = []
            md5_line = None

            for line in lines:
                if line.startswith('MD5:'):
                    md5_line = line
                    continue
                formatted_lines.append(line)

            # Junta todas as linhas exceto MD5
            formatted_content = '\n'.join(formatted_lines)

            # Se encontrou MD5, adiciona duas linhas antes
            if md5_line:
                formatted_content = formatted_content.rstrip() + '\n\n' + md5_line

            self.snapshot_text.insert(tk.END, formatted_content)
            self.snapshot_text.config(state=tk.DISABLED)

    def copiar_conteudo_snapshot(self):
        """
        Copia o conteúdo do snapshot atual para a área de transferência.
        """
        conteudo = self.snapshot_text.get("1.0", tk.END).strip()
        if conteudo:
            self.root.clipboard_clear()
            self.root.clipboard_append(conteudo)
            mostrar_sucesso(self.root, "Conteúdo copiado para a área de transferência!")

    def criar_backup(self):
        """Cria um backup dos arquivos do aplicativo"""
        # Obtém a data atual no formato "ddmmyyyy"
        data_atual = datetime.now().strftime("%d%m%Y")

        # Verifica se já existe um backup com a data atual
        backup_existente = list(self.backup_dir.glob(f"backup_{data_atual}_*.zip"))

        # Se já existir um backup com a data atual, não cria um novo
        if backup_existente:
            print(f"Backup do dia {data_atual} já existe. Ignorando criação de novo backup.")
            return

        # Se não existir, cria um novo backup com a data e hora atual
        timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
        backup_file = self.backup_dir / f"backup_{timestamp}.zip"

        with zipfile.ZipFile(backup_file, "w") as zipf:
            for root_dir, dirs, files in os.walk(self.base_dir):
                # Ignora a pasta de backups durante o backup
                if "backups" in root_dir:
                    continue
                for file in files:
                    file_path = os.path.join(root_dir, file)
                    zipf.write(
                        file_path,
                        os.path.relpath(file_path, self.base_dir),
                    )

        # Limita o número de backups
        backups = sorted(self.backup_dir.glob("backup_*.zip"), key=os.path.getmtime)
        while len(backups) > 15:
            backups[0].unlink()
            backups.pop(0)

    def carregar_configuracoes_janela(self):
        config_path = self.config_dir / "config_janela.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.root.geometry(f"{config['largura']}x{config['altura']}+{config['pos_x']}+{config['pos_y']}")

    def salvar_configuracoes_janela(self):
        # Obtém a geometria da janela (formato: "LARGURAxALTURA+X+Y")
        geometria = self.root.geometry()

        # Divide a string em partes
        partes = geometria.split("+")
        if len(partes) != 3:
            return  # Se o formato não for válido, ignora

        # Extrai largura e altura (partes[0] = "LARGURAxALTURA")
        dimensoes = partes[0].split("x")
        if len(dimensoes) != 2:
            return  # Se o formato não for válido, ignora

        largura = int(dimensoes[0])
        altura = int(dimensoes[1])

        # Extrai posição X e Y
        pos_x = int(partes[1])
        pos_y = int(partes[2])

        # Salva as configurações
        config = {
            "largura": largura,
            "altura": altura,
            "pos_x": pos_x,
            "pos_y": pos_y,
        }

        with open(self.config_dir / "config_janela.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        # Salva também as configurações das colunas
        self.salvar_larguras_colunas()

    def ajustar_tamanho_posicao_janela(self):
        largura_tela = self.root.winfo_screenwidth()
        altura_tela = self.root.winfo_screenheight()

        largura_janela = self.root.winfo_width()
        altura_janela = self.root.winfo_height()

        pos_x = self.root.winfo_x()
        pos_y = self.root.winfo_y()

        if pos_x + largura_janela > largura_tela:
            pos_x = largura_tela - largura_janela
        if pos_y + altura_janela > altura_tela:
            pos_y = altura_tela - altura_janela

        self.root.geometry(f"+{pos_x}+{pos_y}")

    def ao_fechar_janela(self):
        self.salvar_configuracoes_janela()
        self.root.destroy()

    def desativar_carregamento_inicial(self):
        """
        Desativa a flag de carregamento inicial após 1 segundos.
        """
        self.carregamento_inicial = False

    def colar_texto_com_substituicao(self, event):
        # Obtém o widget que recebeu o evento
        widget = event.widget

        # Verifica se há texto selecionado
        if widget.tag_ranges(tk.SEL):
            # Remove o texto selecionado
            widget.delete(tk.SEL_FIRST, tk.SEL_LAST)

        # Cola o conteúdo do clipboard
        widget.insert(tk.INSERT, widget.clipboard_get())

        # Retorna 'break' para evitar a execução do comportamento padrão
        return 'break'

    def configurar_atalhos_janela(self, janela, widgets_texto):
        """
        Configura atalhos globais (como Ctrl+A) para uma janela específica
        :param janela: A janela principal (self.root, self.janela_anotacoes, etc.)
        :param widgets_texto: Lista de widgets de texto onde os atalhos devem funcionar
        """
        def selecionar_tudo(event):
            widget = janela.focus_get()  # Obtém o widget com foco
            if widget in widgets_texto:  # Verifica se é um widget de texto
                widget.tag_add(tk.SEL, "1.0", tk.END)
                widget.mark_set(tk.INSERT, "1.0")
                widget.see(tk.INSERT)
                return 'break'  # Impede a propagação do evento
        janela.bind("<Control-a>", selecionar_tudo)
        janela.bind("<Control-A>", selecionar_tudo)  # Para Caps Lock

    def copiar_dados_do_atendimento(self, window, atendimento):
        """Lida com o clique no botão de copiar dados"""
        if self.copiar_dados_atendimento(atendimento):
            mostrar_sucesso(window, "Dados do atendimento copiados para a área de transferência!")
        else:
            mostrar_erro(window, "Erro ao copiar dados do atendimento.")

    def ordenar_arquivos_alfabeticamente(self):
        """Ordena alfabeticamente os conteúdos dos arquivos clientes.txt e dos arquivos na pasta usuarios"""
        try:
            # Ordena o arquivo clientes.txt
            clientes_file = self.base_dir / "clientes.txt"
            if clientes_file.exists():
                with open(clientes_file, "r", encoding="utf-8") as f:
                    linhas = [linha.strip() for linha in f.readlines() if linha.strip()]

                # Remove duplicatas e ordena
                linhas_unicas = list(set(linhas))
                linhas_ordenadas = sorted(linhas_unicas, key=lambda x: x.lower())

                # Reescreve o arquivo
                with open(clientes_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(linhas_ordenadas) + "\n")

            # Ordena os arquivos na pasta usuarios
            if self.usuarios_dir.exists():
                for arquivo in self.usuarios_dir.glob("*.txt"):
                    with open(arquivo, "r", encoding="utf-8") as f:
                        linhas = [linha.strip() for linha in f.readlines() if linha.strip()]

                    # Remove duplicatas e ordena
                    linhas_unicas = list(set(linhas))
                    linhas_ordenadas = sorted(linhas_unicas, key=lambda x: x.lower())

                    # Reescreve o arquivo
                    with open(arquivo, "w", encoding="utf-8") as f:
                        f.write("\n".join(linhas_ordenadas) + "\n")

        except Exception as e:
            print(f"Erro ao ordenar arquivos: {e}")

    def configurar_estilo_menu_linux(self):
        """Configurações específicas para estilização no Linux"""
        style = ttk.Style()
        style.configure('TMenubutton', background='lightgray')
        style.map('TMenubutton',
                background=[('active', 'lightgray')],
                foreground=[('active', 'green')])

        #Criar janela e o sistema de busca

    def criar_janela_busca(self):
        """Cria uma janela de busca avançada para clientes e usuários"""
        if hasattr(self, 'janela_busca') and self.janela_busca.winfo_exists():
            self.janela_busca.lift()
            return

        self.janela_busca = tk.Toplevel(self.root)
        self.janela_busca.title("Busca Avançada")
        self.janela_busca.geometry("970x680")

        # Frame principal
        main_frame = ttk.Frame(self.janela_busca)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Frame de critérios de busca
        criteria_frame = ttk.LabelFrame(main_frame, text="Critérios de Busca")
        criteria_frame.pack(fill=tk.X, pady=5)

        # Cliente (agora com Combobox)
        ttk.Label(criteria_frame, text="Cliente:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.busca_cliente_combobox = ttk.Combobox(criteria_frame, width=30)
        self.busca_cliente_combobox.grid(row=0, column=1, sticky=tk.W, padx=5)
        self.busca_cliente_combobox['values'] = self.clientes
        self.busca_cliente_combobox.bind('<<ComboboxSelected>>', self.atualizar_usuarios_busca)

        # Usuário (agora com Combobox)
        ttk.Label(criteria_frame, text="Usuário:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.busca_usuario_combobox = ttk.Combobox(criteria_frame, width=30)
        self.busca_usuario_combobox.grid(row=0, column=3, sticky=tk.W, padx=5)

        # Ano
        ttk.Label(criteria_frame, text="Ano:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.busca_ano_combobox = ttk.Combobox(criteria_frame, width=8)
        self.busca_ano_combobox.grid(row=1, column=1, sticky=tk.W, padx=5)

        # Mês
        ttk.Label(criteria_frame, text="Mês:").grid(row=1, column=2, sticky=tk.W, padx=5)
        meses = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        self.busca_mes_combobox = ttk.Combobox(criteria_frame, values=meses, width=10)
        self.busca_mes_combobox.grid(row=1, column=3, sticky=tk.W, padx=5)

        # Dia (novo campo)
        ttk.Label(criteria_frame, text="Dia:").grid(row=1, column=4, sticky=tk.W, padx=5)
        dias = [""] + [str(i) for i in range(1, 32)]
        self.busca_dia_combobox = ttk.Combobox(criteria_frame, values=dias, width=5)
        self.busca_dia_combobox.grid(row=1, column=5, sticky=tk.W, padx=5)

        # Tipo
        ttk.Label(criteria_frame, text="Tipo:").grid(row=2, column=0, sticky=tk.W, padx=5)
        self.busca_tipo_combobox = ttk.Combobox(criteria_frame,
                                            values=["Todos", "Presencial", "Remoto"],
                                            width=10)
        self.busca_tipo_combobox.grid(row=2, column=1, sticky=tk.W, padx=5)
        self.busca_tipo_combobox.set("Todos")

        # Situação
        ttk.Label(criteria_frame, text="Situação:").grid(row=2, column=2, sticky=tk.W, padx=5)
        self.busca_situacao_combobox = ttk.Combobox(criteria_frame,
                                                values=["Todos", "Processado", "Não Processado", "Cancelado"],
                                                width=15)
        self.busca_situacao_combobox.grid(row=2, column=3, sticky=tk.W, padx=5)
        self.busca_situacao_combobox.set("Todos")

        # Adicionar novo campo de busca por palavras-chave
        ttk.Label(criteria_frame, text="Palavras-chave:").grid(row=3, column=0, sticky=tk.W, padx=5)
        self.busca_palavras_entry = ttk.Entry(criteria_frame, width=40)
        self.busca_palavras_entry.grid(row=3, column=1, columnspan=3, sticky=tk.W, padx=5)
        ttk.Label(criteria_frame, text="(busca em Problema/Tarefa)").grid(row=3, column=3, sticky=tk.W, padx=5)

        # Botões de ação
        btn_frame = ttk.Frame(criteria_frame)
        btn_frame.grid(row=4, column=0, columnspan=6, pady=10)

        ttk.Button(btn_frame, text="Buscar", command=self.executar_busca).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Limpar", command=self.limpar_busca).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Abrir Espelhamentos",
                command=self.abrir_espelhamentos_busca).pack(side=tk.LEFT, padx=5)

        # Frame de resultados
        results_frame = ttk.LabelFrame(main_frame, text="Resultados")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Treeview para resultados
        self.busca_tree = ttk.Treeview(results_frame,
                                        columns=("Cliente", "Usuário", "Problema", "Data", "Tipo", "Situação", "Tempo"),
                                    show="headings")
        self.busca_tree.pack(fill=tk.BOTH, expand=True)

        # Configurar colunas
        colunas = [("Cliente", 180), ("Usuário", 120), ("Problema", 250), ("Data", 80),
                ("Tipo", 80), ("Situação", 100), ("Tempo", 60)]
        for col, width in colunas:
            self.busca_tree.heading(col, text=col)
            self.busca_tree.column(col, width=width, anchor=tk.W)

        # Barra de rolagem
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.busca_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.busca_tree.configure(yscrollcommand=scrollbar.set)

        # Configurar tags para cores

        style = ttk.Style()
        style.configure("Red.Treeview", foreground="red")
        style.configure("Green.Treeview", foreground="green")
        style.configure("Orange.Treeview", foreground="orange")

        self.busca_tree.tag_configure('aberto', foreground='red')
        self.busca_tree.tag_configure('processado', foreground='green')
        self.busca_tree.tag_configure('nao_processado', foreground='black')
        self.busca_tree.tag_configure('cancelado', foreground='orange')
        self.busca_tree.tag_configure('presencial', font=('Helvetica', 10, 'bold'))
        self.busca_tree.tag_configure('presencial_processado', foreground='green', font=('Helvetica', 10, 'bold'))

        # Evento de duplo clique - agora chama a janela de detalhes existente
        self.busca_tree.bind("<Double-1>", self.abrir_detalhes_selecionado_busca)

        # Carregar anos disponíveis
        self.carregar_anos_disponiveis()

    def carregar_anos_disponiveis(self):
        """Carrega anos disponíveis na NOVA estrutura atendimentos/"""
        anos = sorted([int(d.name) for d in self.atendimentos_dir.iterdir()
                    if d.is_dir() and d.name.isdigit()], reverse=True)
        self.busca_ano_combobox["values"] = anos
        if anos:
            self.busca_ano_combobox.set(anos[0])

    def atualizar_usuarios_busca(self, event=None):
        """Atualiza a lista de usuários quando um cliente é selecionado"""
        cliente = self.busca_cliente_combobox.get()
        usuarios = self.carregar_usuarios_para_cliente(cliente)
        self.busca_usuario_combobox['values'] = usuarios

    def abrir_detalhes_selecionado_busca(self, event):
        """Abre a janela de detalhes para o item selecionado na busca"""
        selecionado = self.busca_tree.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione um atendimento para visualizar os detalhes.")
            return

        item = selecionado[0]

        # Obtém o índice do item selecionado na treeview
        indice = self.busca_tree.index(item)

        # Verifica se o índice está dentro dos resultados armazenados
        if hasattr(self, 'resultados_busca_completos') and 0 <= indice < len(self.resultados_busca_completos):
            atendimento = self.resultados_busca_completos[indice]
            self.visualizar_detalhes_busca(atendimento)
        else:
            messagebox.showwarning("Aviso", "Não foi possível encontrar os detalhes deste atendimento.")

    def limpar_busca(self):
        """Limpa todos os critérios de busca e os resultados"""
        # Limpa os campos de entrada
        self.busca_cliente_combobox.set('')
        self.busca_usuario_combobox.set('')
        self.busca_usuario_combobox['values'] = []
        self.busca_ano_combobox.set('Todos')
        self.busca_mes_combobox.set('')
        self.busca_dia_combobox.set('')
        self.busca_tipo_combobox.set('Todos')
        self.busca_situacao_combobox.set('Todos')
        self.busca_palavras_entry.delete(0, tk.END)

        # Limpa a treeview de resultados
        for item in self.busca_tree.get_children():
            self.busca_tree.delete(item)

        # Limpa os resultados armazenados
        if hasattr(self, 'resultados_busca_completos'):
            del self.resultados_busca_completos

    def executar_busca(self):
        # Limpa resultados anteriores
        for item in self.busca_tree.get_children():
            self.busca_tree.delete(item)

        # Obtém critérios
        cliente = self.busca_cliente_combobox.get().strip()
        usuario = self.busca_usuario_combobox.get().strip()
        ano = self.busca_ano_combobox.get()
        mes = self.busca_mes_combobox.get().lower() if self.busca_mes_combobox.get() else ""
        dia = self.busca_dia_combobox.get()
        tipo = self.busca_tipo_combobox.get()
        situacao = self.busca_situacao_combobox.get()
        palavras = [p.lower() for p in self.busca_palavras_entry.get().strip().split() if p]

        # Executa buscas
        resultados = []
        resultados.extend(self.buscar_atendimentos_concluidos(cliente, usuario, ano, mes, dia, tipo, situacao, palavras))

        if situacao in ["Todos", "Cancelado"]:
            resultados.extend(self.buscar_atendimentos_cancelados(cliente, usuario, ano, mes, dia, palavras))

        if situacao in ["Todos", "Não Processado"]:
            resultados.extend(self.buscar_atendimentos_abertos(cliente, usuario, palavras))

        # Armazena resultados completos mantendo a ordem da treeview
        self.resultados_busca_completos = []

        # Função auxiliar para obter data ou datetime.min se None
        def get_data_safe(atend):
            data = atend.get("data_inicio")
            return data if data is not None else datetime.min.date()

        # Configura tags para cores - ADICIONE ESTAS LINHAS
        self.busca_tree.tag_configure('aberto', foreground='red')
        self.busca_tree.tag_configure('processado', foreground='green')
        self.busca_tree.tag_configure('nao_processado', foreground='black')
        self.busca_tree.tag_configure('cancelado', foreground='orange')

        # Preenche a treeview e armazena os resultados na mesma ordem
        for atend in sorted(resultados, key=lambda x: get_data_safe(x), reverse=True):

            # Prepara o texto do problema resumido
            problema = atend.get("problema", "")
            problema_resumido = (problema[:50] + "...") if len(problema) > 50 else problema

            tags = []
            if atend["situacao"] == "Processado":
                if atend.get("tipo") == "Presencial":
                    tags.append('presencial_processado')
                else:
                    tags.append('processado')
            elif atend["situacao"] == "Cancelado":
                tags.append('cancelado')
                tags.append('bold') # Negrito
            elif atend.get("tipo") == "Em aberto":
                tags.append('aberto')
                tags.append('bold') # Negrito
            elif atend.get("tipo") == "Presencial":
                tags.append('presencial')
            else:
                tags.append('nao_processado')

            tempo = atend.get("tempo_total", "N/A")
            if isinstance(tempo, timedelta):
                horas = int(tempo.total_seconds() // 3600)
                minutos = int((tempo.total_seconds() % 3600) // 60)
                tempo = f"{horas:02d}:{minutos:02d}"

            self.busca_tree.tag_configure('bold', font=('Helvetica', 10, 'bold'))

            # Insere na treeview
            self.busca_tree.insert("", tk.END,
                                values=(
                                    atend["cliente"],
                                    atend.get("usuario", ""),
                                    problema_resumido,
                                    atend["data_inicio"].strftime("%d/%m/%Y") if atend.get("data_inicio") else "N/A",
                                    atend.get("tipo", "Remoto"),
                                    atend["situacao"],
                                    tempo
                                ),
                                tags=tuple(tags))

            # Armazena o atendimento na mesma ordem
            self.resultados_busca_completos.append(atend)

    def buscar_atendimentos_concluidos(self, cliente, usuario, ano, mes, dia, tipo, situacao, palavras):
        """Busca atendimentos concluídos na NOVA estrutura atendimentos/ano/mês/"""
        resultados = []

        # Determina anos para buscar
        anos = []
        if ano and ano != "Todos":
            anos = [ano]
        else:
            anos = [d.name for d in self.atendimentos_dir.iterdir() if d.is_dir() and d.name.isdigit()]

        for ano_dir in anos:
            ano_path = self.atendimentos_dir / ano_dir

            # Determina meses para buscar
            meses = []
            if mes:
                meses = [mes]
            else:
                meses = [d.name for d in ano_path.iterdir() if d.is_dir()]

            for mes_dir in meses:
                mes_path = ano_path / mes_dir
                todos_path = mes_path / "todos.txt"

                if not todos_path.exists():
                    continue

                with open(todos_path, "r", encoding="utf-8") as f:
                    atendimentos = self.parse_arquivo_historico(f.read())

                for atend in atendimentos:
                    # Aplica filtros
                    if cliente and cliente.lower() not in atend["cliente"].lower():
                        continue
                    if usuario and usuario.lower() not in atend.get("usuario", "").lower():
                        continue
                    if tipo != "Todos" and tipo != atend.get("tipo", "Remoto"):
                        continue

                    # Filtro por dia
                    if dia and atend.get("eventos"):
                        data_inicio = atend["eventos"][0]["data"]
                        if str(data_inicio.day) != dia:
                            continue

                    # Verifica situação na NOVA estrutura
                    situacao_atend = self.verificar_status_atendimento(atend)
                    if situacao != "Todos" and situacao != situacao_atend:
                        continue

                    # Filtro por palavras-chave
                    if palavras:
                        problema = atend.get("problema", "").lower()
                        tarefa = atend.get("tarefa", "").lower()
                        if not any(palavra in problema or palavra in tarefa for palavra in palavras):
                            continue

                    # Adiciona informações adicionais
                    atend["situacao"] = situacao_atend
                    atend["data_inicio"] = atend["eventos"][0]["data"] if atend["eventos"] else None
                    resultados.append(atend)

        return resultados

    def buscar_atendimentos_cancelados(self, cliente, usuario, ano, mes, dia, palavras):
        """Busca atendimentos cancelados na NOVA estrutura atendimentos/ano/mês/desistente.txt"""
        resultados = []

        anos = []
        if ano == "Todos":
            anos = [d.name for d in self.atendimentos_dir.iterdir() if d.is_dir() and d.name.isdigit()]
        else:
            anos = [ano]

        for ano_dir in anos:
            ano_path = self.atendimentos_dir / ano_dir

            meses = []
            if mes:
                meses = [mes]
            else:
                meses = [d.name for d in ano_path.iterdir() if d.is_dir()]

            for mes_dir in meses:
                mes_path = ano_path / mes_dir
                desistente_path = mes_path / "desistente.txt"

                if not desistente_path.exists():
                    continue

                with open(desistente_path, "r", encoding="utf-8") as f:
                    blocos = f.read().split("----------------------------------\n")

                for bloco in blocos:
                    if not bloco.strip():
                        continue

                    dados = {}
                    for linha in bloco.split("\n"):
                        if ":" in linha:
                            chave, valor = linha.split(":", 1)
                            dados[chave.strip()] = valor.strip()

                    # Aplica filtros
                    if cliente and cliente.lower() not in dados.get("Cliente", "").lower():
                        continue
                    if usuario and usuario.lower() not in dados.get("Usuário", "").lower():
                        continue

                    try:
                        data = datetime.strptime(dados.get("Data", ""), "%d/%m/%Y").date()
                    except:
                        data = None

                    if dia and data and str(data.day) != dia:
                        continue
                    if ano != "Todos" and data and str(data.year) != ano:
                        continue
                    if mes and data and data.strftime("%B").lower() != mes:
                        continue

                    if palavras:
                        problema = dados.get("Problema", "").lower()
                        tarefa = dados.get("Tarefa", "").lower()
                        if not any(p in problema or p in tarefa for p in palavras):
                            continue

                    atendimento = {
                        "cliente": dados.get("Cliente", ""),
                        "usuario": dados.get("Usuário", ""),
                        "problema": dados.get("Problema", ""),
                        "tarefa": dados.get("Tarefa", ""),
                        "data_inicio": data,
                        "tempo_total": "00:00",
                        "situacao": "Cancelado",
                        "tipo": "Cancelado",
                        "eventos": [{"tipo": "inicio", "data": data, "hora": time(0, 0)}] if data else []
                    }
                    resultados.append(atendimento)

        return resultados

    def buscar_atendimentos_abertos(self, cliente, usuario, palavras):
        """Busca atendimentos em aberto (tmp_atendimentos)"""
        resultados = []

        for chave, atendimento in self.tmp_atendimentos.items():
            # Aplica filtros
            if cliente and cliente.lower() not in atendimento["cliente"].lower():
                continue
            if usuario and usuario.lower() not in atendimento.get("usuario", "").lower():
                continue

            # Aplica filtro de palavras-chave
            if palavras:
                problema = atendimento.get("problema", "").lower()
                tarefa = atendimento.get("tarefa", "").lower()
                encontrou = False

                for palavra in palavras:
                    if palavra in problema or palavra in tarefa:
                        encontrou = True
                        break

                if not encontrou:
                    continue

            # Adiciona informações adicionais
            atendimento["situacao"] = "Não Processado"
            atendimento["data_inicio"] = atendimento["eventos"][0]["data"] if atendimento["eventos"] else None
            atendimento["tempo_total"] = "Em aberto"
            atendimento["tipo"] = "Em aberto"

            resultados.append(atendimento)

        return resultados

    def visualizar_detalhes_busca(self, atendimento):
        """Adaptação da função visualizar_detalhes para funcionar com a busca"""
        # Cria uma cópia do atendimento para não modificar o original
        original_atendimento = copy.deepcopy(atendimento)

        # Verifica se é um atendimento da busca ou um tmp_atendimento
        is_tmp_atendimento = not original_atendimento.get("finalizado", True)

        # Armazena o número do atendimento
        numero_atendimento = original_atendimento.get("numero_atendimento", "")

        # Cria a janela de detalhes como filha da janela de busca
        detalhes_window = tk.Toplevel(self.janela_busca)
        detalhes_window.title("Detalhes do Atendimento")
        detalhes_window.geometry("720x580")

        # Armazena informações importantes na janela
        detalhes_window.numero_atendimento = numero_atendimento
        detalhes_window.original_atendimento = original_atendimento
        detalhes_window.is_tmp_atendimento = is_tmp_atendimento

        # Frame principal
        main_frame = ttk.Frame(detalhes_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        # Adiciona uma linha separadora
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        # Botão Editar
        edit_button = ttk.Button(
            btn_frame,
            text="Editar",
            command=lambda: self.toggle_edit(detalhes_window, True),
        )
        edit_button.pack(side=tk.LEFT, padx=5)

        # Botão Salvar - modificado para usar a função correta
        save_button = ttk.Button(
            btn_frame,
            text="Salvar",
            command=lambda: self.salvar_edicao_busca(detalhes_window),
        )
        save_button.pack(side=tk.LEFT, padx=5)
        save_button.config(state=tk.DISABLED)

        # Botão Remover - modificado para funcionar com busca
        remove_button = ttk.Button(
            btn_frame,
            text="Remover este Atendimento",
            command=lambda: self.remover_atendimento_busca(detalhes_window),
        )
        remove_button.pack(side=tk.LEFT, padx=5)

        # Botão Copiar
        ttk.Button(
            btn_frame,
            text="Copiar dados do atendimento",
            command=lambda: self.copiar_dados_do_atendimento(detalhes_window, original_atendimento)
        ).pack(side=tk.LEFT, padx=5)

        fields_frame = ttk.Frame(main_frame)
        fields_frame.pack(fill=tk.BOTH, expand=True)

        # Botão de status (só para atendimentos finalizados)
        if not is_tmp_atendimento and original_atendimento.get("situacao") != "Cancelado":
            self.status_btn = ttk.Button(
                btn_frame,
                text="Não Processado",
                style="Red.TButton",
                command=lambda: self.alternar_status_atendimento(detalhes_window, original_atendimento)
            )
            self.status_btn.pack(side=tk.LEFT, padx=5)

            # Configura o estilo dos botões de status
            style = ttk.Style()
            style.configure("Red.TButton", foreground="white", background="red", font=('Helvetica', 10, 'bold'))
            style.configure("Green.TButton", foreground="white", background="green", font=('Helvetica', 10, 'bold'))

            # Verifica o status atual e configura o botão
            self.verificar_status_botao(original_atendimento)

        # Adiciona uma linha separadora
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        # Frame para informações do atendimento
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=5)

        # Campos de informações do atendimento
        ttk.Label(info_frame, text="Atendente:", font=('Helvetica', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Label(info_frame, text=original_atendimento.get('numero_atendimento', 'N/A').split(' - ')[0],
                font=('Helvetica', 10)).grid(row=0, column=1, sticky=tk.W)

        ttk.Label(info_frame, text="Nº do atendimento:", font=('Helvetica', 10, 'bold')).grid(row=0, column=2, sticky=tk.W, padx=5)
        ttk.Label(info_frame, text=original_atendimento.get('numero_atendimento', 'N/A').split(' - ')[-1],
                font=('Helvetica', 10)).grid(row=0, column=3, sticky=tk.W)

        ttk.Label(info_frame, text="Tipo:", font=('Helvetica', 10, 'bold')).grid(row=0, column=4, sticky=tk.W, padx=5)
        tipo = original_atendimento.get('tipo', 'Remoto')
        ttk.Label(info_frame, text=tipo, font=('Helvetica', 10)).grid(row=0, column=5, sticky=tk.W)

        # Campos de detalhes
        ttk.Label(fields_frame, text="Cliente:").grid(row=0, column=0, sticky=tk.W)
        cliente_label = ttk.Label(fields_frame, text=original_atendimento["cliente"])
        cliente_label.grid(row=0, column=1, sticky=tk.W)

        ttk.Label(fields_frame, text="Usuário:").grid(row=1, column=0, sticky=tk.W)
        usuario_label = ttk.Label(fields_frame, text=original_atendimento.get("usuario", "N/A"))
        usuario_label.grid(row=1, column=1, sticky=tk.W)

        ttk.Label(fields_frame, text="Data Inicial:").grid(row=2, column=0, sticky=tk.W)
        data_inicial = (
            original_atendimento["eventos"][0]["data"].strftime("%d/%m/%Y")
            if original_atendimento["eventos"]
            else "N/A"
        )
        data_label = ttk.Label(fields_frame, text=data_inicial)
        data_label.grid(row=2, column=1, sticky=tk.W)

        ttk.Label(fields_frame, text="Hora Inicial:").grid(row=3, column=0, sticky=tk.W)
        hora_inicial = (
            original_atendimento["eventos"][0]["hora"].strftime("%H:%M")
            if original_atendimento["eventos"]
            else "N/A"
        )
        hora_label = ttk.Label(fields_frame, text=hora_inicial)
        hora_label.grid(row=3, column=1, sticky=tk.W)

        # Campos editáveis
        ttk.Label(fields_frame, text="Problema a resolver:").grid(row=4, column=0, sticky=tk.W)
        problema_entry = scrolledtext.ScrolledText(
            fields_frame,
            width=80,
            height=4,
            wrap=tk.WORD
        )
        problema_entry.grid(row=4, column=1, sticky=tk.W)
        problema_entry.insert(1.0, original_atendimento.get("problema", ""))
        problema_entry.bind("<<Paste>>", self.colar_texto_com_substituicao)
        problema_entry.config(state=tk.DISABLED)
        # Adiciona menu de contexto
        problema_entry.bind("<Button-3>", lambda e: self.criar_menu_contexto_generico(e, detalhes_window))

        ttk.Label(fields_frame, text="Tarefa realizada:").grid(row=5, column=0, sticky=tk.W)
        tarefa_entry = scrolledtext.ScrolledText(
            fields_frame,
            width=80,
            height=8,
            wrap=tk.WORD
        )
        tarefa_entry.grid(row=5, column=1, sticky=tk.W)
        tarefa_entry.insert(1.0, original_atendimento.get("tarefa", ""))
        tarefa_entry.bind("<<Paste>>", self.colar_texto_com_substituicao)
        tarefa_entry.config(state=tk.DISABLED)
        # Adiciona menu de contexto
        tarefa_entry.bind("<Button-3>", lambda e: self.criar_menu_contexto_generico(e, detalhes_window))

        ttk.Label(fields_frame, text="Histórico de Eventos:").grid(row=6, column=0, sticky=tk.W)
        eventos_text = scrolledtext.ScrolledText(fields_frame, width=30, height=10)
        eventos_str = "\n".join(
            [
                f"{'Início' if e['tipo'] == 'inicio' else e['tipo'].capitalize()}: {e['data'].strftime('%d/%m/%Y')} {e['hora'].strftime('%H:%M')}"
                for e in original_atendimento["eventos"]
            ]
        )
        eventos_text.insert(tk.END, eventos_str)
        eventos_text.grid(row=6, column=1, sticky=tk.W)
        eventos_text.config(state=tk.DISABLED)

        # Tempo total - agora trata strings e timedelta
        tempo_total = original_atendimento.get("tempo_total", "N/A")
        if isinstance(tempo_total, timedelta):
            horas = int(tempo_total.total_seconds() // 3600)
            minutos = int((tempo_total.total_seconds() % 3600) // 60)
            tempo_str = f"{horas:02d}:{minutos:02d}"
        else:
            tempo_str = str(tempo_total)  # Pode ser "00:00", "Em aberto", etc.

        ttk.Label(fields_frame, text="Tempo Total:").grid(row=7, column=0, sticky=tk.W)
        tempo_label = ttk.Label(fields_frame, text=tempo_str)
        tempo_label.grid(row=7, column=1, sticky=tk.W)

        # Armazena referências aos widgets na janela
        detalhes_window.problema_entry = problema_entry
        detalhes_window.tarefa_entry = tarefa_entry
        detalhes_window.eventos_text = eventos_text
        detalhes_window.edit_button = edit_button
        detalhes_window.save_button = save_button

        # Configura atalhos para janela
        self.configurar_atalhos_janela(
            detalhes_window,
            [problema_entry, tarefa_entry, eventos_text]
        )
        # Foca na janela de detalhes
        detalhes_window.focus_set()

        # Atualiza a interface
        detalhes_window.update()

    def salvar_edicao_busca(self, window):
        """Salva as alterações feitas em um atendimento da busca"""
        try:
            # Obtém os dados da janela
            original_atendimento = window.original_atendimento
            is_tmp_atendimento = window.is_tmp_atendimento

            # Cria uma cópia do atendimento original para modificar
            new_atendimento = copy.deepcopy(original_atendimento)

            # Atualiza os campos com os valores editados
            new_atendimento["problema"] = window.problema_entry.get("1.0", tk.END).strip()
            new_atendimento["tarefa"] = window.tarefa_entry.get("1.0", tk.END).strip()

            # Parseia os eventos (se foram editados)
            new_eventos = window.eventos_text.get("1.0", tk.END).strip()
            try:
                eventos = self.parse_eventos(new_eventos)
                new_atendimento["eventos"] = eventos
            except ValueError as e:
                mostrar_erro(window, f"Formato inválido no histórico de eventos: {str(e)}")
                return

            # Recalcula o tempo total
            tempo_total = self.calcular_tempo_total_eventos(eventos)
            new_atendimento["tempo_total"] = tempo_total

            # Diferencia entre atendimentos temporários e finalizados
            if is_tmp_atendimento:
                # Atualiza o tmp_atendimentos
                chave_composta = f"{new_atendimento['cliente']} – {new_atendimento['usuario']}"
                if chave_composta in self.tmp_atendimentos:
                    self.tmp_atendimentos[chave_composta] = new_atendimento
                    self.salvar_tmp_atendimentos()
            else:
                # Atualiza os arquivos na estrutura de pastas
                data_inicio = new_atendimento["eventos"][0]["data"]
                ano_dir = self.atendimentos_dir / str(data_inicio.year)
                mes_dir = ano_dir / data_inicio.strftime("%B").lower()

                # Atualiza todos.txt
                todos_path = mes_dir / "todos.txt"
                if todos_path.exists():
                    with open(todos_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    original_block = self.formatar_atendimento(original_atendimento)
                    new_block = self.formatar_atendimento(new_atendimento)
                    new_content = content.replace(original_block, new_block)

                    with open(todos_path, "w", encoding="utf-8") as f:
                        f.write(new_content)

                # Atualiza o arquivo do cliente
                cliente_path = mes_dir / f"{new_atendimento['cliente']}.txt"
                if cliente_path.exists():
                    with open(cliente_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    new_content = content.replace(original_block, new_block)
                    with open(cliente_path, "w", encoding="utf-8") as f:
                        f.write(new_content)

            # Atualiza a lista de resultados da busca
            if hasattr(self, 'resultados_busca_completos'):
                for i, atend in enumerate(self.resultados_busca_completos):
                    if (atend.get("cliente") == original_atendimento["cliente"] and
                        atend.get("usuario") == original_atendimento.get("usuario", "") and
                        ((atend.get("eventos") and atend["eventos"][0]["data"] == original_atendimento["eventos"][0]["data"]) or
                        (not atend.get("eventos") and not original_atendimento.get("eventos")))):

                        self.resultados_busca_completos[i] = new_atendimento
                        break

            # Atualiza a treeview
            self.executar_busca()

            # Fecha a janela de detalhes
            window.destroy()

            mostrar_sucesso(self.janela_busca, "Atendimento atualizado com sucesso!")

        except Exception as e:
            mostrar_erro(window, f"Erro ao salvar alterações: {str(e)}")
            print(f"Erro detalhado: {traceback.format_exc()}")

    def remover_atendimento_busca(self, window):
        """Remove um atendimento da janela de busca"""
        original_atendimento = window.original_atendimento
        is_tmp_atendimento = window.is_tmp_atendimento

        confirmacao = messagebox.askyesno(
            "Confirmar Remoção",
            "Tem certeza que deseja remover este atendimento?",
            parent=window
        )

        if not confirmacao:
            return

        try:
            if is_tmp_atendimento:
                # Remove de tmp_atendimentos
                chave_composta = f"{original_atendimento['cliente']} – {original_atendimento['usuario']}"
                if chave_composta in self.tmp_atendimentos:
                    del self.tmp_atendimentos[chave_composta]
                    self.salvar_tmp_atendimentos()
            else:
                # Remove dos arquivos na estrutura de pastas
                data_inicio = original_atendimento["eventos"][0]["data"]
                ano_dir = self.atendimentos_dir / str(data_inicio.year)
                mes_dir = ano_dir / data_inicio.strftime("%B").lower()

                # Remove de todos.txt
                todos_path = mes_dir / "todos.txt"
                if todos_path.exists():
                    with open(todos_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    original_block = self.formatar_atendimento(original_atendimento)
                    new_content = content.replace(original_block, "")

                    with open(todos_path, "w", encoding="utf-8") as f:
                        f.write(new_content)

                # Remove do arquivo do cliente
                cliente_path = mes_dir / f"{original_atendimento['cliente']}.txt"
                if cliente_path.exists():
                    with open(cliente_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    new_content = content.replace(original_block, "")
                    with open(cliente_path, "w", encoding="utf-8") as f:
                        f.write(new_content)

                # Remove do status.txt
                status_path = mes_dir / "status.txt"
                if status_path.exists():
                    with open(status_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Extrai apenas o número do atendimento
                    numero_atendimento = original_atendimento.get("numero_atendimento", "").split(" - ")[-1]

                    # Divide em blocos e remove o bloco correspondente
                    blocos = content.split("**********************************\n")
                    novo_conteudo = []

                    for bloco in blocos:
                        if f"Número do atendimento: {numero_atendimento}" not in bloco:
                            novo_conteudo.append(bloco)

                    # Reconstrói o arquivo
                    new_content = "**********************************\n".join(novo_conteudo)
                    if content.endswith("**********************************\n"):
                        new_content += "\n**********************************\n"

                    with open(status_path, "w", encoding="utf-8") as f:
                        f.write(new_content)

            # Atualiza a lista de resultados da busca
            if hasattr(self, 'resultados_busca_completos'):
                self.resultados_busca_completos = [
                    atend for atend in self.resultados_busca_completos
                    if not (atend.get("cliente") == original_atendimento["cliente"] and
                        atend.get("usuario") == original_atendimento.get("usuario", "") and
                        ((atend.get("eventos") and atend["eventos"][0]["data"] == original_atendimento["eventos"][0]["data"]) or
                            (not atend.get("eventos") and not original_atendimento.get("eventos"))))
                ]

            # Atualiza a treeview
            self.executar_busca()

            # Fecha a janela de detalhes
            window.destroy()

            mostrar_sucesso(self.janela_busca, "Atendimento removido com sucesso!")

        except Exception as e:
            mostrar_erro(window, f"Erro ao remover atendimento: {str(e)}")
            print(f"Erro detalhado: {traceback.format_exc()}")

    def abrir_espelhamentos_busca(self):
        """Abre a janela de espelhamentos para o cliente-usuário da busca"""
        selecionado = self.busca_tree.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione um item para abrir os espelhamentos.")
            return

        item = selecionado[0]
        valores = self.busca_tree.item(item, 'values')

        # Define o cliente e usuário nos campos principais
        self.cliente_var.set(valores[0])
        self.usuario_var.set(valores[1])

        # Abre a janela de espelhamentos
        self.criar_janela_espelhamentos()

if __name__ == "__main__":
    root = tk.Tk()
    app = AtendimentoApp(root)
    root.mainloop()
