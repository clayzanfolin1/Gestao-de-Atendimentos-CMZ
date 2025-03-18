import os
import json
import zipfile
import copy
from datetime import datetime, date, time, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import platform
import locale
import hashlib
from tkinter import Toplevel, messagebox
from tkinter import Menu
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

        # Ajusta o tamanho e a posição da janela
        self.ajustar_tamanho_posicao_janela()

        # Mantém a janela acima da barra de tarefas
        #self.root.wm_attributes("-topmost", 1)

        # Flag para controlar o carregamento inicial
        self.carregamento_inicial = True

        # Define a pasta base de acordo com o sistema operacional
        if platform.system() == "Linux":
            # No Linux/macOS, usa a pasta home com um ponto no início
            self.base_dir = Path.home() / ".cmz-atendimentos-teste" #CMZ
            #self.base_dir = Path.home() / "Trabalho" / "Marcelo"/ "chamados" /"cmz-atendimentos" #millan
        else:
            # No Windows, usa a pasta AppData\Local
            self.base_dir = Path.home() / "AppData" / "Local" / "cmz-atendimentos"

        # Cria a pasta de dados do usuário
        self.dados_usuario_dir = self.base_dir / "dados do usuario"
        self.dados_usuario_dir.mkdir(parents=True, exist_ok=True)

        # Cria a pasta de usuários
        self.usuarios_dir = self.base_dir / "usuarios"
        self.usuarios_dir.mkdir(parents=True, exist_ok=True)

        # Cria a pasta de configurações
        self.config_dir = self.base_dir / "configuracoes"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Carrega as configurações da janela
        self.carregar_configuracoes_janela()

        # Configura o locale para português do Brasil
        configurar_locale_pt_br()

        # Cria a pasta se ela não existir
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Criação do menu superior
        self.criar_menu_superior()

        # Variável para controlar o estado da hora automática
        self.hora_automatica = True

        # Inicia a atualização automática da hora
        self.atualizar_hora()

        # Cria as pastas do ano e do mês corrente, se não existirem
        self.criar_pasta_ano_mes_corrente()

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
        self.criar_widgets_principais()
        self.criar_backup()

        # Atualiza a navegação temporal e carrega o histórico do mês atual
        self.atualizar_navegacao_temporal()
        self.carregar_historico()
        # Agenda a desativação da flag após 2 segundos
        self.root.after(1000, self.desativar_carregamento_inicial)  # 1000 ms = 2 segundos

    def criar_menu_contexto(self, event):
        """
        Cria um menu de contexto com as opções de selecionar tudo, copiar, recortar e colar.
        Fecha o menu após 500 ms.
        """
        menu = Menu(None, tearoff=0)
        menu.add_command(label="Selecionar Tudo", command=lambda: event.widget.tag_add(tk.SEL, "1.0", tk.END))
        menu.add_command(label="Copiar", command=lambda: event.widget.event_generate("<<Copy>>"))
        menu.add_command(label="Recortar", command=lambda: event.widget.event_generate("<<Cut>>"))
        menu.add_command(label="Colar", command=lambda: event.widget.event_generate("<<Paste>>"))

        # Exibe o menu na posição do clique
        menu.post(event.x_root, event.y_root)

        # Fecha o menu após 500 ms
        self.root.after(3000, menu.unpost)

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

        # Cria o diretório do ano e do mês, se não existirem
        mes_dir = self.base_dir / ano_atual / mes_atual
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

        # Botão "Diretório"
        menubar.add_command(label="Diretório", command=self.abrir_diretorio)

        # Botão "Espelhamentos"
        menubar.add_command(label="Espelhamentos", command=self.criar_janela_espelhamentos)

        # Botão "Sobre"
        menubar.add_command(label="Sobre", command=self.mostrar_sobre)

        # Configura o menu na janela principal
        self.root.config(menu=menubar)

        # Cria um Frame para a barra de ferramentas (toolbar)
        toolbar = tk.Frame(self.root)  # Use tk.Frame em vez de ttk.Frame
        toolbar.pack(side=tk.TOP, fill=tk.X)

        # Adiciona o botão de controle da hora automática à toolbar
        self.botao_hora_automatica = tk.Button(  # Use tk.Button em vez de ttk.Button
            toolbar,
            text="Desligar Hora Automática",
            command=self.alternar_hora_automatica,
            foreground="black"  # Cor padrão do texto
        )
        self.botao_hora_automatica.pack(side=tk.LEFT, padx=5, pady=2)

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

    def mostrar_sobre(self):
        """
        Exibe uma caixa de mensagem com informações sobre o desenvolvedor, licença e versão do software.
        """
        sobre_texto = (
            "Desenvolvedor: Clayton Magalhães Zanfolin   \n\n" "Direitos de uso: Licença Pública Geral GNU versão 2.0   \n\n" "Versão: 1.0   "
        )
        messagebox.showinfo("Sobre", sobre_texto)

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

        # Novo frame de rodapé no painel esquerdo
        #left_footer = ttk.Frame(left_panel)
        #left_footer.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

        # Botão de controle da hora automática
        #self.botao_hora_automatica = ttk.Button(
            #left_footer,
            #text="Desligar Hora Automática",
            #command=self.alternar_hora_automatica,
        #)
        #self.botao_hora_automatica.pack(expand=True)  # Centralizado

        # Painel Direito (mantido igual)
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        self.criar_secao_historico(right_panel)

    def criar_secao_dados_usuario(self, parent):
        frame = ttk.LabelFrame(parent, text="Dados do Usuário")
        frame.pack(fill=tk.X, pady=5, expand=False)

        self.dados_usuario_text = scrolledtext.ScrolledText(frame, height=10, width=40)
        self.dados_usuario_text.pack(fill=tk.X, padx=5, pady=5)

        # Adiciona as funcionalidades de selecionar tudo e menu de contexto
        self.adicionar_funcionalidades_texto(self.dados_usuario_text)  # Usar self para chamar o método

        # Bind text modification to save
        self.dados_usuario_text.bind("<KeyRelease>", self.salvar_dados_usuario)

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
            self.salvar_atendimento_temporario()
            self.carregar_atendimento_temporario(chave_composta)
            self.atualizar_lista_abertos()

            # Carregar os dados do usuário se o arquivo existir
            cliente = self.tmp_atendimentos[chave_composta]["cliente"].strip()
            usuario = self.tmp_atendimentos[chave_composta]["usuario"].strip()
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
                ano_dir = self.base_dir / str(data.year)
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
            self.estado_atual = dados["estado"]

            # Verifica se o último evento foi uma pausa
            if self.eventos and self.eventos[-1]["tipo"] == "pausa":
                # Se o último evento foi uma pausa, o estado deve ser "pausado"
                self.estado_atual = ESTADOS[2]  # "pausado"
            else:
                # Caso contrário, o estado deve ser "em_andamento"
                self.estado_atual = ESTADOS[1]  # "em_andamento"

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
            side=tk.TOP, fill=tk.X, pady=2  # Alterado para TOP e fill X
        )
        ttk.Button(btn_frame, text="Iniciar Cliente", width=5, command=self.selecionar_cliente).pack(
            side=tk.TOP, fill=tk.X, pady=2  # Alterado para TOP e fill X
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
            self.atendimento_frame, height=3, width=40
        )
        self.problema_entry.grid(row=2, column=0, columnspan=2, padx=5, pady=2)

        # Adiciona as funcionalidades de selecionar tudo e menu de contexto ao campo "Problema a resolver"
        self.adicionar_funcionalidades_texto(self.problema_entry)


        ttk.Label(self.atendimento_frame, text="Tarefa realizada:").grid(
            row=3, column=0, sticky=tk.W
        )
        self.tarefa_entry = scrolledtext.ScrolledText(
            self.atendimento_frame, height=3, width=40
        )
        self.tarefa_entry.grid(row=4, column=0, columnspan=2, padx=5, pady=2)

        # Adiciona as funcionalidades de selecionar tudo e menu de contexto ao campo "Tarefa realizada"
        self.adicionar_funcionalidades_texto(self.tarefa_entry)

        self.dynamic_frame = ttk.Frame(self.atendimento_frame)
        self.dynamic_frame.grid(row=5, column=0, columnspan=2, pady=5)

        self.btn_frame = ttk.Frame(self.atendimento_frame)
        self.btn_frame.grid(row=6, column=0, columnspan=2, pady=5)

        self.iniciar_novo_atendimento()

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
            self.estado_atual = ESTADOS[1]  # "em_andamento"

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

        ano_dir = self.base_dir / str(data.year)
        mes_dir = ano_dir / data.strftime("%B").lower()
        mes_dir.mkdir(parents=True, exist_ok=True)

        todos_path = mes_dir / "todos.txt"
        with open(todos_path, "a", encoding="utf-8") as f:
            f.write(self.formatar_atendimento(self.current_atendimento))

        cliente_path = mes_dir / f"{self.current_atendimento['cliente']}.txt"
        with open(cliente_path, "a", encoding="utf-8") as f:
            f.write(self.formatar_atendimento(self.current_atendimento))

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
            eventos_str.append(f"{evento['tipo'].upper()}: {data_str} {hora_str}")

        tempo_total = atendimento.get("tempo_total", timedelta())
        horas = int(tempo_total.total_seconds() // 3600)
        minutos = int((tempo_total.total_seconds() % 3600) // 60)

        return (
            "**********************************\n"
            f"Nome do Cliente: {atendimento['cliente']}\n"
            f"Usuário: {atendimento.get('usuario', '')}\n\n"
            f"Problema a resolver: {atendimento['problema']}\n\n"
            f"Tarefa realizada: {atendimento['tarefa']}\n\n"
            "Histórico de Eventos:\n" + "\n".join(eventos_str) + "\n\n"
            f"Tempo Total: {horas:02d}:{minutos:02d}\n"
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

        self.tree = ttk.Treeview(
            frame,
            columns=("Cliente", "Data", "Problema", "Tarefa", "Tempo"),
            show="headings",
        )
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        colunas = [
            ("Cliente", 150),
            ("Data", 80),
            ("Problema", 200),
            ("Tarefa", 200),
            ("Tempo", 80),
        ]
        for col, width in colunas:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor=tk.W)

        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scroll.set)

        self.tree.bind("<Double-1>", self.visualizar_detalhes)
        self.atualizar_navegacao_temporal()

    def atualizar_navegacao_temporal(self):
        # Obtém o ano e o mês atuais
        ano_atual = datetime.now().year
        mes_atual = datetime.now().strftime("%B")  # Nome completo do mês (ex: "Janeiro")

        # Obtém os anos disponíveis
        anos = set()
        for entry in self.base_dir.iterdir():
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

    def carregar_historico(self):
        ano = self.ano_combobox.get()
        mes = self.mes_combobox.get().lower()

        if not ano or not mes:
            return

        # Verifica se o diretório do mês existe
        mes_dir = self.base_dir / ano / mes
        if not mes_dir.exists():
            # Limpa a lista de histórico se o diretório não existir
            for item in self.tree.get_children():
                self.tree.delete(item)
            # Exibe uma mensagem apenas se não for o carregamento inicial
            if not self.carregamento_inicial:
                messagebox.showinfo(
                    "Sem dados",
                    f"Não há dados disponíveis para {mes.capitalize()} de {ano}.",
                )
            return

        # Verifica se o arquivo todos.txt existe e está vazio
        todos_path = mes_dir / "todos.txt"
        if not todos_path.exists() or todos_path.stat().st_size == 0:
            # Limpa a lista de histórico
            for item in self.tree.get_children():
                self.tree.delete(item)
            # Exibe uma mensagem apenas se não for o carregamento inicial
            if not self.carregamento_inicial:
                messagebox.showinfo(
                    "Sem dados",
                    f"Não há dados disponíveis para {mes.capitalize()} de {ano}.",
                )
            return

        # Limpa a lista de histórico antes de carregar
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Carrega o histórico do arquivo todos.txt
        self.current_historico = []
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

        self.tree.tag_configure(
            "aberto", foreground="red", font=("Helvetica", 10, "bold")
        )

        # Desativa a flag de carregamento inicial após o primeiro uso
        if self.carregamento_inicial:
            self.carregamento_inicial = False

    def parse_arquivo_historico(self, conteudo):
        atendimentos = []
        blocos = conteudo.split("**********************************\n")

        for bloco in blocos:
            if not bloco.strip():
                continue

            atend = {"eventos": []}
            lines = bloco.strip().split("\n")
            for line in lines:
                if line.startswith("Nome do Cliente:"):
                    atend["cliente"] = line.split(": ")[1].strip()
                elif line.startswith("Usuário:"):
                    atend["usuario"] = line.split(": ")[1].strip()
                elif line.startswith("Problema a resolver:"):
                    atend["problema"] = line.split(": ")[1].strip()
                elif line.startswith("Tarefa realizada:"):
                    atend["tarefa"] = line.split(": ")[1].strip()
                elif line.startswith("Tempo Total:"):
                    tempo = line.split(": ")[1].strip()
                    horas, minutos = map(int, tempo.split(":"))
                    atend["tempo_total"] = timedelta(hours=horas, minutes=minutos)
                elif any(
                    line.startswith(tipo)
                    for tipo in ["INICIO:", "PAUSA:", "RETOMADA:", "FIM:"]
                ):
                    partes = line.split()
                    tipo = partes[0].replace(":", "").lower()
                    data_str = partes[1]
                    hora_str = partes[2]
                    atend["eventos"].append(
                        {
                            "tipo": tipo,
                            "data": datetime.strptime(data_str, "%d/%m/%Y").date(),
                            "hora": datetime.strptime(hora_str, "%H:%M").time(),
                        }
                    )

            if atend:
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

        detalhes_window = tk.Toplevel(self.root)
        detalhes_window.title("Detalhes do Atendimento")
        detalhes_window.geometry("800x600")

        main_frame = ttk.Frame(detalhes_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)

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

        # Adiciona o botão "Remover este Atendimento"
        remove_button = ttk.Button(
            btn_frame,
            text="Remover este Atendimento",
            command=lambda: self.remover_atendimento(original_atendimento, detalhes_window),
        )
        remove_button.pack(side=tk.LEFT, padx=5)

        fields_frame = ttk.Frame(main_frame)
        fields_frame.pack(fill=tk.BOTH, expand=True)

        fields_frame = ttk.Frame(main_frame)
        fields_frame.pack(fill=tk.BOTH, expand=True)

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
        problema_entry = scrolledtext.ScrolledText(fields_frame, width=60, height=4)
        problema_entry.insert(tk.END, atendimento["problema"])
        problema_entry.grid(row=4, column=1, sticky=tk.W)
        problema_entry.config(state=tk.DISABLED)
         # Adiciona as funcionalidades de selecionar tudo e menu de contexto ao campo "Problema a resolver"
        self.adicionar_funcionalidades_texto(problema_entry)

        ttk.Label(fields_frame, text="Tarefa realizada:").grid(row=5, column=0, sticky=tk.W)
        tarefa_entry = scrolledtext.ScrolledText(fields_frame, width=60, height=4)
        tarefa_entry.insert(tk.END, atendimento["tarefa"])
        tarefa_entry.grid(row=5, column=1, sticky=tk.W)
        tarefa_entry.config(state=tk.DISABLED)
        # Adiciona as funcionalidades de selecionar tudo e menu de contexto ao campo "Tarefa realizada"
        self.adicionar_funcionalidades_texto(tarefa_entry)

        ttk.Label(fields_frame, text="Histórico de Eventos:").grid(row=6, column=0, sticky=tk.W)
        eventos_text = scrolledtext.ScrolledText(fields_frame, width=60, height=6)
        eventos_str = "\n".join(
            [
                f"{e['tipo'].capitalize()}: {e['data'].strftime('%d/%m/%Y')} {e['hora'].strftime('%H:%M')}"
                for e in atendimento["eventos"]
            ]
        )
        eventos_text.insert(tk.END, eventos_str)
        eventos_text.grid(row=6, column=1, sticky=tk.W)
        eventos_text.config(state=tk.DISABLED)

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

    def toggle_edit(self, window, enable):
        state = tk.NORMAL if enable else tk.DISABLED
        window.problema_entry.config(state=state)
        window.tarefa_entry.config(state=state)
        window.eventos_text.config(state=state)
        window.edit_button.config(state=tk.DISABLED if enable else tk.NORMAL)
        window.save_button.config(state=tk.NORMAL if enable else tk.DISABLED)

    def salvar_edicao(self, original_atendimento, window):
        """
        Salva as alterações feitas no atendimento e atualiza o arquivo todos.txt.
        """
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
        data_inicio = original_atendimento["eventos"][0]["data"]
        ano = data_inicio.year
        mes = data_inicio.strftime("%B").lower()
        mes_dir = self.base_dir / str(ano) / mes
        todos_path = mes_dir / "todos.txt"

        # Atualiza o arquivo todos.txt
        if todos_path.exists():
            with open(todos_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Substitui o bloco original pelo novo bloco
            new_content = content.replace(original_block, new_block)

            # Salva o conteúdo atualizado no arquivo
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
        ano = data_inicio.year
        mes = data_inicio.strftime("%B").lower()
        mes_dir = self.base_dir / str(ano) / mes
        todos_path = mes_dir / "todos.txt"

        # Remove o atendimento do arquivo todos.txt
        if todos_path.exists():
            with open(todos_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Remove o bloco do atendimento
            original_block = self.formatar_atendimento(atendimento)
            new_content = content.replace(original_block, "")

            # Salva o conteúdo atualizado no arquivo
            with open(todos_path, "w", encoding="utf-8") as f:
                f.write(new_content)

        # Remove o atendimento do arquivo do cliente, se existir
        cliente_path = mes_dir / f"{atendimento['cliente']}.txt"
        if cliente_path.exists():
            with open(cliente_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Remove o bloco do atendimento
            new_content = content.replace(original_block, "")

            # Salva o conteúdo atualizado no arquivo
            with open(cliente_path, "w", encoding="utf-8") as f:
                f.write(new_content)

        # Adiciona o atendimento removido ao arquivo desistente.txt
        desistente_path = mes_dir / "desistente.txt"
        with open(desistente_path, "a", encoding="utf-8") as f:
            f.write(
                f"Cliente: {atendimento['cliente']}\n"
                f"Usuário: {atendimento.get('usuario', '')}\n"
                f"Problema: {atendimento['problema']}\n"
                f"Tarefa: {atendimento['tarefa']}\n"
                f"Data: {data_inicio.strftime('%d/%m/%Y')}\n"
                f"Tempo: 00:00\n"  # Tempo total pode ser ajustado se necessário
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

            # Verifica se a linha começa com um tipo de evento válido
            if any(line.startswith(tipo) for tipo in ["início:", "inicio:", "pausa:", "retomada:", "fim:"]):
                # Divide o tipo do evento e o restante da linha
                partes = line.split(":", 1)  # Divide apenas no primeiro ":"
                if len(partes) < 2:
                    raise ValueError(f"Formato inválido na linha: {line}")

                tipo = partes[0].strip()
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
        # Obtém o cliente e usuário atualmente selecionados
        cliente = self.cliente_var.get().strip()
        usuario = self.usuario_var.get().strip()

        if not cliente or not usuario:
            mostrar_erro(self.root, "Selecione um cliente e usuário antes de abrir os espelhamentos.")
            return

        espelhamentos_window = tk.Toplevel(self.root)
        espelhamentos_window.title(f"Espelhamentos - {cliente} - {usuario}")
        espelhamentos_window.geometry("800x600")

        # Frame principal
        main_frame = ttk.Frame(espelhamentos_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Frame para a lista de snapshots
        lista_frame = ttk.Frame(main_frame)
        lista_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # Lista de snapshots
        ttk.Label(lista_frame, text="Snapshots:").pack()
        self.lista_snapshots = tk.Listbox(lista_frame, width=30, height=20)


        self.lista_snapshots.pack(fill=tk.Y, expand=True)
        self.lista_snapshots.bind("<<ListboxSelect>>", self.carregar_snapshot_selecionado)

        # Frame para o conteúdo do snapshot
        conteudo_frame = ttk.Frame(main_frame)
        conteudo_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Área de texto para exibir o conteúdo do snapshot
        ttk.Label(conteudo_frame, text="Conteúdo do Snapshot:").pack()
        self.snapshot_text = scrolledtext.ScrolledText(conteudo_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.snapshot_text.pack(fill=tk.BOTH, expand=True)

        # Botão para copiar o conteúdo
        ttk.Button(conteudo_frame, text="Copiar Conteúdo", command=self.copiar_conteudo_snapshot).pack(pady=5)

        # Carregar os snapshots disponíveis para o cliente e usuário atuais
        self.carregar_snapshots(cliente, usuario)

    def carregar_snapshots(self, cliente, usuario):
        """
        Carrega os snapshots disponíveis na lista para o cliente e usuário especificados.
        """
        self.lista_snapshots.delete(0, tk.END)
        self.snapshots = []

        # Define o nome do arquivo de snapshot esperado
        nome_arquivo = f"{cliente}-{usuario}.old".replace("/", "_")

        # Verifica se o arquivo de snapshot existe
        arquivo_snapshot = self.dados_usuario_dir / nome_arquivo
        if not arquivo_snapshot.exists():
            mostrar_erro(self.root, f"Nenhum snapshot encontrado para {cliente} - {usuario}.")
            return

        # Lê o conteúdo do arquivo de snapshot
        with open(arquivo_snapshot, "r", encoding="utf-8") as f:
            linhas = f.readlines()

        # Processa o conteúdo do arquivo de snapshot
        snapshots = []
        snapshot_atual = []
        for linha in linhas:
            if linha.startswith("Espelhado na data:"):
                if snapshot_atual:
                    snapshots.append(("".join(snapshot_atual)))
                    snapshot_atual = []
            snapshot_atual.append(linha)
        if snapshot_atual:
            snapshots.append(("".join(snapshot_atual)))

        # Adiciona os snapshots à lista
        for i, snapshot in enumerate(snapshots, start=1):
            data_hora = snapshot.split("\n")[0].replace("Espelhado na data: ", "")
            self.snapshots.append((data_hora, snapshot))
            self.lista_snapshots.insert(tk.END, f"Snapshot {i} - {data_hora}")

        # Ordena os snapshots por data e hora (do mais recente para o mais antigo)
        self.snapshots.sort(reverse=True, key=lambda x: datetime.strptime(x[0], "%d/%m/%Y Hora: %H:%M"))
        self.lista_snapshots.delete(0, tk.END)
        for snapshot in self.snapshots:
            self.lista_snapshots.insert(tk.END, f"Snapshot - {snapshot[0]}")

    def carregar_snapshot_selecionado(self, event=None):
        """
        Carrega o conteúdo do snapshot selecionado na área de texto.
        """
        selecionado = self.lista_snapshots.curselection()
        if not selecionado:
            return

        # Obtém o snapshot selecionado
        data_hora = self.lista_snapshots.get(selecionado[0])
        snapshot = next((snap[1] for snap in self.snapshots if snap[0] in data_hora), None)

        if snapshot:
            # Exibe o conteúdo no widget de texto
            self.snapshot_text.config(state=tk.NORMAL)
            self.snapshot_text.delete("1.0", tk.END)
            self.snapshot_text.insert(tk.END, snapshot)
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
        backup_dir = self.base_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        # Obtém a data atual no formato "ddmmyyyy"
        data_atual = datetime.now().strftime("%d%m%Y")

        # Verifica se já existe um backup com a data atual
        backup_existente = list(backup_dir.glob(f"backup_{data_atual}_*.zip"))

        # Se já existir um backup com a data atual, não cria um novo
        if backup_existente:
            print(f"Backup do dia {data_atual} já existe. Ignorando criação de novo backup.")
            return

        # Se não existir, cria um novo backup com a data e hora atual
        timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
        backup_file = backup_dir / f"backup_{timestamp}.zip"

        with zipfile.ZipFile(backup_file, "w") as zipf:
            for root, dirs, files in os.walk(self.base_dir):
                if "backups" in root:
                    continue
                for file in files:
                    zipf.write(
                        os.path.join(root, file),
                        os.path.relpath(os.path.join(root, file), self.base_dir),
                    )

        # Limita o número de backups mantidos (opcional)
        backups = sorted(backup_dir.glob("backup_*.zip"), key=os.path.getmtime)
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


if __name__ == "__main__":
    root = tk.Tk()
    app = AtendimentoApp(root)
    root.mainloop()
