import tkinter as tk
from tkinter import ttk, StringVar, messagebox, filedialog
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import Image, ImageTk
import os
import sys
import traceback
import threading
import pythoncom
from datetime import date
from custom_widgets import EntryWithPlaceholder
from file_processing import DocumentProcessor
import ast


def resource_path(relative_path):
    try:
        # PyInstaller cria uma pasta temporária e armazena o caminho em _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Se não estiver rodando como .exe, usa o caminho normal
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# --- Constantes de Estilo e Configuração ---
APP_TITLE = "Conversor IN's SOC"
MAIN_BG_COLOR = '#2B2B2B'
FRAME_BG_COLOR = '#3C3F41'
TEXT_COLOR = '#FFFFFF'
ACCENT_COLOR = '#007ACC'
ENTRY_BG_COLOR = '#4A4A4A'
FONT_FAMILY = "Segoe UI"
FONT_SIZE_NORMAL = 10
FONT_SIZE_BOLD = 11
FONT_SIZE_TITLE = 22

FRETE_OPTIONS = ["Selecione o frete", "Frete CIF", "Frete FOB", "Frete Indisponível", "Frete incluso", "Valor"]
UNITY_OPTIONS = ["Selecione a unidade", "m", "m²", "m³", "Unidade", "Litro", "Outro"]
MO_OPTIONS = ["Mão de obra?", "Sim", "Não", "Mão de obra inclusa"]

PLACEHOLDERS = {
    "insumo": "Insumo Principal (Ex: Bloco de Concreto)",
    "item_num": "Número do Item/Código",
    "unidade": "Unidade (Ex: m², Un, Kg)",
    "fornecedor": "Nome do Fornecedor",
    "data": "Data (dd/mm/aaaa)",
    "valor_insumo": "Valor do Insumo",
    "valor_frete": "Valor do Frete",
    "valor_mo": "Valor da Mão de Obra",
    "fonte": "Fonte da Cotação (Ex: Email, Telefone)",
    "outro_unidade": "Digite a unidade"
}


class MainApplication:
    def __init__(self, master_window):
        self.master = master_window
        self.master.title(APP_TITLE)
        self.master.configure(bg=MAIN_BG_COLOR)
        self.master.geometry('1020x800')
        self.master.resizable(False, False)

        self.logo_image = self._load_logo('logo.png', (64, 64))
        self.png_conversion_status = [0, 0, 0]

        self._configure_styles()
        self._initialize_frames()
        self._create_widgets()
        self._layout_frames()

        self.status_bar.config(text="Pronto.")

    def _load_logo(self, filename, size):
        """Carrega a imagem do logo usando resource_path."""
        path = resource_path(filename)
        try:
            return ImageTk.PhotoImage(Image.open(path).resize(size, Image.Resampling.LANCZOS))
        except Exception as e:
            print(f"Aviso: Logo não encontrado ou falha ao carregar '{path}': {e}")
            # Cria uma imagem placeholder para não quebrar o layout
            return ImageTk.PhotoImage(Image.new('RGB', size, 'grey'))

    def _configure_styles(self):
        self.style = ttk.Style(self.master)
        self.style.theme_use('clam')
        self.style.configure('.', background=FRAME_BG_COLOR, foreground=TEXT_COLOR,
                             font=(FONT_FAMILY, FONT_SIZE_NORMAL), borderwidth=1)
        self.style.configure('TFrame', background=FRAME_BG_COLOR)
        self.style.configure('Header.TFrame', background=MAIN_BG_COLOR)
        self.style.configure('TLabel', background=FRAME_BG_COLOR, foreground=TEXT_COLOR)
        self.style.configure('Header.TLabel', background=MAIN_BG_COLOR, foreground=TEXT_COLOR)
        self.style.configure('Status.TLabel', background=MAIN_BG_COLOR, foreground='#999999')
        self.style.configure('TButton', font=(FONT_FAMILY, FONT_SIZE_BOLD), background=ACCENT_COLOR, foreground='white',
                             borderwidth=0, padding=(10, 8))
        self.style.map('TButton', background=[('active', '#009CFF'), ('pressed', '#005A9E'), ('disabled', '#555555')])
        self.style.configure('TEntry', fieldbackground=ENTRY_BG_COLOR, foreground=TEXT_COLOR, insertcolor=TEXT_COLOR,
                             bordercolor=FRAME_BG_COLOR)
        self.master.option_add('*TCombobox*Listbox.background', ENTRY_BG_COLOR)
        self.master.option_add('*TCombobox*Listbox.foreground', TEXT_COLOR)
        self.master.option_add('*TCombobox*Listbox.selectBackground', ACCENT_COLOR)
        self.master.option_add('*TCombobox*Listbox.selectForeground', 'white')
        self.style.configure('TCombobox', fieldbackground=ENTRY_BG_COLOR, foreground=TEXT_COLOR, arrowcolor='white',
                             bordercolor=FRAME_BG_COLOR, selectbackground=ENTRY_BG_COLOR)
        self.style.map('TCombobox', fieldbackground=[('readonly', ENTRY_BG_COLOR)])
        self.style.configure('TCheckbutton', indicatorcolor=ENTRY_BG_COLOR, padding=5)
        self.style.map('TCheckbutton', indicatorcolor=[('selected', ACCENT_COLOR)])

    def _initialize_frames(self):
        self.header_frame = ttk.Frame(self.master, style='Header.TFrame', padding=(10, 15))
        self.general_params_frame = ttk.Frame(self.master, padding=(15, 5))
        self.supplier_frames = [ttk.Frame(self.master, padding=15) for _ in range(3)]
        self.bottom_frame = ttk.Frame(self.master, padding=(15, 10))
        self.status_bar_frame = ttk.Frame(self.master, style='Header.TFrame',
                                          height=25)  # Usando Header.TFrame para combinar o BG

    def _create_supplier_column_widgets(self, parent_frame, col_index):
        widgets = {}
        ttk.Label(parent_frame, text=f"Fornecedor {col_index + 1}", font=(FONT_FAMILY, FONT_SIZE_BOLD)).pack(
            anchor='center', pady=(0, 10))

        style = ttk.Style()
        style.configure('Custom.TButton', padding=(0, 0))

        for key in ["fornecedor", "data", "valor_insumo"]:
            if key == "data":
                data_frame = ttk.Frame(parent_frame)
                data_frame.pack(pady=4, fill='x')

                widgets[key] = EntryWithPlaceholder(data_frame, PLACEHOLDERS[key])
                widgets[key].pack(side='left', fill='x', expand=True)

                btn_hoje = ttk.Button(
                    data_frame,
                    text="Hoje",
                    command=lambda e=widgets[key]: e.set_value(date.today().strftime("%d/%m/%Y")),
                    style='Custom.TButton'
                )
                btn_hoje.pack(side='left', padx=(5, 0))
            else:
                widgets[key] = EntryWithPlaceholder(parent_frame, PLACEHOLDERS[key])
                widgets[key].pack(pady=4, fill='x')

        frete_frame = ttk.Frame(parent_frame)
        frete_frame.pack(fill='x')
        widgets['frete_combo'] = ttk.Combobox(frete_frame, values=FRETE_OPTIONS, state="readonly")
        widgets['frete_combo'].current(0)
        widgets['frete_combo'].pack(pady=4, fill='x')
        widgets['valor_frete_entry'] = EntryWithPlaceholder(frete_frame, PLACEHOLDERS["valor_frete"])
        widgets['valor_frete_entry'].pack(fill='x', pady=(0, 4))
        widgets['valor_frete_entry'].pack_forget()

        mo_frame = ttk.Frame(parent_frame)
        mo_frame.pack(fill='x')
        widgets['mo_combo'] = ttk.Combobox(mo_frame, values=MO_OPTIONS, state="readonly")
        widgets['mo_combo'].current(0)
        widgets['mo_combo'].pack(pady=4, fill='x')
        widgets['valor_mo_entry'] = EntryWithPlaceholder(mo_frame, PLACEHOLDERS["valor_mo"])
        widgets['valor_mo_entry'].pack(fill='x', pady=(0, 4))
        widgets['valor_mo_entry'].pack_forget()

        widgets['frete_combo'].bind("<<ComboboxSelected>>",
                                    lambda e, w=widgets: self._handle_combo_selection(w['valor_frete_entry'],
                                                                                      w['frete_combo'], "Valor"))
        widgets['mo_combo'].bind("<<ComboboxSelected>>",
                                 lambda e, w=widgets: self._handle_combo_selection(w['valor_mo_entry'], w['mo_combo'],
                                                                                   "Sim"))
        widgets['fonte_entry'] = EntryWithPlaceholder(parent_frame, PLACEHOLDERS["fonte"])
        widgets['fonte_entry'].pack(pady=(15, 4), fill='x')
        ttk.Label(parent_frame, text="Anexo da cotação:").pack(anchor='w', pady=(15, 2))
        anexo_frame = ttk.Frame(parent_frame)
        anexo_frame.pack(fill='x')
        widgets['file_path_var'] = StringVar()
        widgets['arquivo_entry'] = ttk.Entry(anexo_frame, textvariable=widgets['file_path_var'], state='readonly')
        widgets['arquivo_entry'].pack(side='left', fill='x', expand=True)
        widgets['browse_button'] = ttk.Button(anexo_frame, text="Procurar...", command=lambda idx=col_index,
                                                                                              svar=widgets[
                                                                                                  'file_path_var']: self._browse_file(
            idx, svar), style='Custom.TButton')
        widgets['browse_button'].pack(side='right', padx=(5, 0))
        parent_frame.drop_target_register(DND_FILES)
        parent_frame.dnd_bind('<<Drop>>',
                              lambda e, idx=col_index, svar=widgets['file_path_var']: self._handle_drop(e, idx, svar))
        return widgets

    def set_workforce(self):
        for col_widgets in self.supplier_widgets_list:
            col_widgets['mo_combo'].set(MO_OPTIONS[2])  # "Não"
            col_widgets['valor_mo_entry'].pack_forget()
        self.status_bar.config(text="Pronto. Definido que não é mão de obra.")

    def set_no_shipping(self):
        for col_widgets in self.supplier_widgets_list:
            col_widgets['frete_combo'].set(FRETE_OPTIONS[3])  # "Frete Indisponível"
            col_widgets['valor_frete_entry'].pack_forget()
        self.status_bar.config(text="Pronto. Definido como frete indisponível.")

    def set_value_shipping(self):
        for col_widgets in self.supplier_widgets_list:
            col_widgets['frete_combo'].set(FRETE_OPTIONS[5])  # "Valor"
            self._handle_combo_selection(col_widgets['valor_frete_entry'], col_widgets['frete_combo'], FRETE_OPTIONS[5])
        self.status_bar.config(text="Pronto. Definido como frete 'Valor'.")

    def clear_half_entries(self):
        for widget in [self.insumo_entry, self.item_num_entry]:
            widget.delete(0, 'end')
            widget.put_placeholder()
        for col_widgets in self.supplier_widgets_list:
            for key in ["valor_insumo", "valor_frete_entry", "valor_mo_entry"]:
                if key in col_widgets:
                    col_widgets[key].delete(0, 'end')
                    col_widgets[key].put_placeholder()
            if 'file_path_var' in col_widgets:
                col_widgets['file_path_var'].set("")
        self.output_dir_entry.delete(0, 'end')
        self.status_bar.config(text="Pronto. Campos de preço e item limpos.")

    def importtxtfile(self):
        caminho_arquivo = filedialog.askopenfilename(
            title="Selecione um arquivo de dados (.txt)",
            filetypes=[("Arquivos de Texto", "*.txt"), ("Todos os arquivos", "*.*")]
        )

        if not caminho_arquivo:
            self.status_bar.config(text="Importação cancelada.")
            return  # Sai da função se nenhum arquivo for selecionado

        try:
            with open(caminho_arquivo, mode='r', encoding='utf-8') as arquivo:
                conteudo_string = arquivo.read()

            # Converte a string em um objeto Python de forma segura
            dados_importados = ast.literal_eval(conteudo_string)

            # **CHAMADA AO NOVO MÉTODO PARA PREENCHER A INTERFACE**
            self._populate_ui_from_data(dados_importados)

        except FileNotFoundError:
            messagebox.showerror("Erro de Arquivo", f"O arquivo '{caminho_arquivo}' não foi encontrado.")
            self.status_bar.config(text="Erro ao ler o arquivo.")
        except (ValueError, SyntaxError) as e:
            messagebox.showerror("Erro de Formato",
                                 f"O conteúdo do arquivo não é válido. Verifique a estrutura.\n\nDetalhes: {e}")
            self.status_bar.config(text="Erro: Formato de arquivo inválido.")
        except Exception as e:
            messagebox.showerror("Erro Inesperado", f"Ocorreu um erro ao processar o arquivo:\n\n{e}")
            self.status_bar.config(text="Erro inesperado durante a importação.")
            traceback.print_exc()

    def _create_widgets(self):
        self.header_frame.grid_columnconfigure(1, weight=1)
        if self.logo_image:
            logo_label = ttk.Label(self.header_frame, image=self.logo_image, style='Header.TLabel')
            logo_label.grid(row=0, column=0, sticky='w', padx=(10, 20))
        title_label = ttk.Label(self.header_frame, text="Conversor IN's SOC",
                                font=(FONT_FAMILY, FONT_SIZE_TITLE, "bold"),
                                style='Header.TLabel')
        title_label.grid(row=0, column=1, sticky='w')

        params_sub_frame = ttk.Frame(self.general_params_frame)
        params_sub_frame.pack(fill='x', expand=True)

        self.item_num_entry = EntryWithPlaceholder(params_sub_frame, PLACEHOLDERS["item_num"])
        self.item_num_entry.pack(side='left', fill='x', expand=True, padx=5)

        self.insumo_entry = EntryWithPlaceholder(params_sub_frame, PLACEHOLDERS["insumo"])
        self.insumo_entry.pack(side='left', fill='x', expand=True, padx=(0, 5))

        self.unidade_entry = ttk.Combobox(params_sub_frame, values=UNITY_OPTIONS, state="readonly")
        self.unidade_entry.current(0)
        self.unidade_entry.pack(side='left', fill='x', expand=True, padx=5)

        self.unidade_outro_entry = EntryWithPlaceholder(params_sub_frame, PLACEHOLDERS["outro_unidade"])
        self.unidade_entry.bind("<<ComboboxSelected>>", self._handle_unidade_selection)

        self.supplier_widgets_list = [self._create_supplier_column_widgets(frame, i) for i, frame in
                                      enumerate(self.supplier_frames)]

        output_frame = ttk.Frame(self.bottom_frame)
        ttk.Label(output_frame, text="Diretório de Saída", font=(FONT_FAMILY, FONT_SIZE_BOLD)).pack(anchor='w')
        self.output_dir_entry = ttk.Entry(output_frame, width=80)
        self.output_dir_entry.pack(fill='x', expand=True, pady=(5, 10))
        self.create_doc_button = ttk.Button(output_frame, text="CRIAR DOCUMENTO FINAL", command=self._trigger_pdffinal)
        self.create_doc_button.pack(fill='x')
        output_frame.grid(row=0, column=0, padx=(0, 20), sticky="ew")

        actions_frame = ttk.Frame(self.bottom_frame)
        ttk.Label(actions_frame, text="Ações Rápidas", font=(FONT_FAMILY, FONT_SIZE_BOLD)).pack(anchor='w', pady=(0, 5))

        # ### INÍCIO DA CORREÇÃO ###
        buttons_subframe = ttk.Frame(actions_frame)

        # Configura as colunas do grid para terem o mesmo peso (para expansão)
        buttons_subframe.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Usa .grid() para TODOS os botões dentro de 'buttons_subframe'
        # Linha 0
        ttk.Button(buttons_subframe, text="Não é MO", command=self.set_workforce).grid(row=0, column=0, padx=5, pady=5,
                                                                                       sticky='ew')
        ttk.Button(buttons_subframe, text="Sem Frete", command=self.set_no_shipping).grid(row=0, column=1, padx=5,
                                                                                          pady=5, sticky='ew')
        ttk.Button(buttons_subframe, text="Frete Valor", command=self.set_value_shipping).grid(row=0, column=2, padx=5,
                                                                                               pady=5, sticky='ew')

        ttk.Button(buttons_subframe, text="Importar", command=self.importtxtfile).grid(row=0, column=3, padx=5, pady=5, sticky='ew')

        # Linha 1
        ttk.Button(buttons_subframe, text="Limpar Tudo", command=self.clear_all_entries).grid(row=1, column=0, padx=5,
                                                                                              pady=5, sticky='ew')
        ttk.Button(buttons_subframe, text="Limpar Valores", command=self.clear_half_entries).grid(row=1, column=1,
                                                                                                  padx=5, pady=5,
                                                                                                  sticky='ew')
        ttk.Button(buttons_subframe, text="Limpar Cache", command=self.perform_desbug).grid(row=1, column=2, padx=5,
                                                                                            pady=5, sticky='ew')
        ttk.Button(buttons_subframe, text="Ajuda", command=self.show_help_window).grid(row=1, column=3, padx=5, pady=5,
                                                                                       sticky='ew')

        # Empacota o frame que contém o grid de botões
        buttons_subframe.pack(fill='x', pady=5)
        # ### FIM DA CORREÇÃO ###

        actions_frame.grid(row=0, column=1, sticky="nsew")

        self.bottom_frame.grid_columnconfigure(0, weight=3)
        self.bottom_frame.grid_columnconfigure(1, weight=1)

        self.status_bar = ttk.Label(self.status_bar_frame, text="Pronto.", style="Status.TLabel", anchor='w')
        self.status_bar.pack(fill='x', padx=10, pady=2)

    def _populate_ui_from_data(self, data):
        """
        Preenche a interface usando o metodo .set_value() nativo dos widgets customizados.
        """
        if not isinstance(data, dict):
            messagebox.showerror("Erro de Formato", "O formato do arquivo é inválido. Era esperado um dicionário.")
            return

        self.clear_all_entries()
        self.status_bar.config(text="Preenchendo formulário com dados importados...")
        self.insumo_entry.set_value(data.get("insumo", ""))
        self.item_num_entry.set_value(data.get("item_num", ""))
        self.output_dir_entry.delete(0, tk.END)
        self.output_dir_entry.insert(0, data.get("output_directory", ""))

        unidade_importada = data.get("unidade", UNITY_OPTIONS[0])
        if unidade_importada in UNITY_OPTIONS:
            self.unidade_entry.set(unidade_importada)
            self.unidade_outro_entry.pack_forget()
        else:
            self.unidade_entry.set("Outro")
            self._handle_unidade_selection(None)
            self.unidade_outro_entry.set_value(unidade_importada)

        # Itera sobre os fornecedores
        for i, supplier_info in enumerate(data.get("fornecedores_data", [])):
            if i >= len(self.supplier_widgets_list): break

            widgets = self.supplier_widgets_list[i]

            widgets['fornecedor'].set_value(supplier_info.get("nome", ""))
            widgets['data'].set_value(supplier_info.get("data_str", ""))
            widgets['valor_insumo'].set_value(str(supplier_info.get("valor_str", "")).replace('.', ','))
            widgets['fonte_entry'].set_value(supplier_info.get("fonte_str", ""))

            widgets['frete_combo'].set(supplier_info.get("frete_tipo", FRETE_OPTIONS[0]))
            widgets['mo_combo'].set(supplier_info.get("mo_tipo", MO_OPTIONS[0]))

            # Mostra e preenche os campos de valor condicional
            self._handle_combo_selection(widgets['valor_frete_entry'], widgets['frete_combo'], "Valor")
            if widgets['frete_combo'].get() == "Valor":
                widgets['valor_frete_entry'].set_value(str(supplier_info.get("frete_valor_str", "")).replace('.', ','))

            self._handle_combo_selection(widgets['valor_mo_entry'], widgets['mo_combo'], "Sim")
            if widgets['mo_combo'].get() == "Sim":
                widgets['valor_mo_entry'].set_value(str(supplier_info.get("mo_valor_str", "")).replace('.', ','))

            caminho_anexo = supplier_info.get("arquivo_path_raw", "")
            if caminho_anexo:
                widgets['file_path_var'].set(caminho_anexo)
                self._process_new_attachment_path(caminho_anexo, i)

        self.status_bar.config(text="Pronto. Dados importados e aplicados com sucesso.")

    def _handle_unidade_selection(self, event):
        """Exibe ou oculta o campo de entrada para unidade customizada."""
        if self.unidade_entry.get() == "Outro":
            self.unidade_outro_entry.pack(side='left', fill='x', expand=True, padx=(5, 0))
        else:
            self.unidade_outro_entry.pack_forget()

    def _layout_frames(self):
        for i in range(3): self.master.grid_columnconfigure(i, weight=1)
        self.master.grid_rowconfigure(2, weight=1)
        self.header_frame.grid(row=0, column=0, columnspan=3, sticky="ew")
        self.general_params_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=10, sticky="ew")
        self.supplier_frames[0].grid(row=2, column=0, padx=(10, 5), pady=10, sticky="nsew")
        self.supplier_frames[1].grid(row=2, column=1, padx=5, pady=10, sticky="nsew")
        self.supplier_frames[2].grid(row=2, column=2, padx=(5, 10), pady=10, sticky="nsew")
        self.bottom_frame.grid(row=3, column=0, columnspan=3, padx=10, pady=(0, 10), sticky="ew")
        self.status_bar_frame.grid(row=4, column=0, columnspan=3, sticky="ew")

    def _process_new_attachment_path(self, file_path, png_index):
        if file_path.lower().endswith((".jpg", ".jpeg", ".png")):
            output_pdf_filename = f"image{png_index + 1}.pdf"
            output_pdf_path = resource_path(output_pdf_filename)
            try:
                self._convert_image_to_pdf(file_path, output_pdf_path)
                self.png_conversion_status[png_index] = 1
                self.status_bar.config(text=f"Imagem '{os.path.basename(file_path)}' convertida para PDF.")
            except Exception as e:
                messagebox.showerror("Erro de Conversão", f"Falha ao converter imagem: {e}")
        else:
            self.png_conversion_status[png_index] = 0
            self.status_bar.config(text=f"Anexo '{os.path.basename(file_path)}' selecionado.")

    def _browse_file(self, col_index, string_var):
        filepath = filedialog.askopenfilename(title="Selecione uma cotação",
                                              filetypes=[("Documentos Suportados", "*.pdf *.jpg *.jpeg *.png"),
                                                         ("Todos os arquivos", "*.*")])
        if filepath:
            string_var.set(filepath)
            self._process_new_attachment_path(filepath, col_index)

    def _handle_drop(self, event, png_index, string_var):
        cleaned_path = event.data.translate({ord("{"): None, ord("}"): None})
        string_var.set(cleaned_path)
        self._process_new_attachment_path(cleaned_path, png_index)

    def _trigger_pdffinal(self):
        output_directory = self.output_dir_entry.get()
        if not output_directory or not os.path.isdir(output_directory):
            messagebox.showerror("Erro de Diretório", "Por favor, especifique um diretório de saída válido.")
            return

        gui_data = self._collect_data_for_processing()
        gui_data['output_directory'] = output_directory

        if not gui_data["fornecedores_data"]:
            messagebox.showwarning("Nenhum Dado", "Nenhum dado de fornecedor preenchido para processar.")
            return

        self.create_doc_button.config(state="disabled")
        self.master.config(cursor="watch")
        self.status_bar.config(text="Processando... Por favor, aguarde.")
        self.master.update_idletasks()

        def process_task():
            pythoncom.CoInitialize()
            try:
                processor = DocumentProcessor(app_base_path=resource_path('.'),
                                              output_target_directory=output_directory, structured_gui_data=gui_data)
                processor.execute()
                self.master.after(0, lambda: self.status_bar.config(text="Processo concluído com sucesso!"))
                self.master.after(0, lambda: messagebox.showinfo("Sucesso",
                                                                 f"Documento 'in.pdf' e 'sga.txt' criados com sucesso em:\n{output_directory}"))
            except Exception as e:
                self.master.after(0,
                                  lambda: self.status_bar.config(text="Erro! Verifique o console para mais detalhes."))
                self.master.after(0, lambda: messagebox.showerror("Erro no Processamento",
                                                                  f"Ocorreu um erro ao criar o documento:\n{e}"))
                traceback.print_exc()
            finally:
                self.master.after(0, lambda: self.create_doc_button.config(state="normal"))
                self.master.after(0, lambda: self.master.config(cursor=""))
                pythoncom.CoUninitialize()

        processing_thread = threading.Thread(target=process_task)
        processing_thread.start()

    def _handle_combo_selection(self, entry_widget, combo_widget, show_condition):
        if combo_widget.get() == show_condition:
            entry_widget.pack(pady=4, fill='x')
        else:
            entry_widget.pack_forget()

    @staticmethod
    def _convert_image_to_pdf(image_path, output_pdf_path):
        with Image.open(image_path) as img:
            if img.mode in ('RGBA', 'P'): img = img.convert('RGB')
            img.save(output_pdf_path, "PDF", resolution=100.0)

    def clear_all_entries(self):
        """Limpa todos os campos de entrada e os reseta para o estado padrão."""
        self.insumo_entry.delete(0, 'end');
        self.insumo_entry.put_placeholder()
        self.item_num_entry.delete(0, 'end');
        self.item_num_entry.put_placeholder()

        self.unidade_entry.set(UNITY_OPTIONS[0])
        self.unidade_outro_entry.delete(0, 'end');
        self.unidade_outro_entry.put_placeholder()
        self.unidade_outro_entry.pack_forget()

        for col_widgets in self.supplier_widgets_list:
            for key in ["fornecedor", "data", "valor_insumo", "fonte_entry", "valor_frete_entry", "valor_mo_entry"]:
                if key in col_widgets:
                    col_widgets[key].delete(0, 'end')
                    col_widgets[key].put_placeholder()

            col_widgets['valor_frete_entry'].pack_forget()
            col_widgets['valor_mo_entry'].pack_forget()
            col_widgets['frete_combo'].set(FRETE_OPTIONS[0])
            col_widgets['mo_combo'].set(MO_OPTIONS[0])
            if 'file_path_var' in col_widgets:
                col_widgets['file_path_var'].set("")

        self.output_dir_entry.delete(0, 'end')
        self.png_conversion_status = [0, 0, 0]
        self.status_bar.config(text="Pronto. Todos os campos foram limpos.")

    def perform_desbug(self):
        temp_files = [f'image{i}.pdf' for i in range(1, 4)] + ['saida.pdf', 'saida_sem_segunda.pdf']
        cleaned_count = 0
        for fname in temp_files:
            fpath = resource_path(fname)
            if os.path.exists(fpath):
                try:
                    os.remove(fpath);
                    cleaned_count += 1
                except OSError as e:
                    print(f"Aviso: Não foi possível remover {fpath}: {e}")
        self.status_bar.config(text=f"{cleaned_count} arquivo(s) temporário(s) removido(s).")
        messagebox.showinfo("Limpar Cache", f"{cleaned_count} arquivo(s) temporário(s) removido(s).")

    def show_help_window(self):
        help_win = tk.Toplevel(self.master)
        help_win.title("Ajuda")
        help_win.configure(bg=FRAME_BG_COLOR)
        help_win.geometry("450x650")
        help_win.resizable(False, False)
        help_win.transient(self.master)
        help_win.grab_set()
        help_content = [("Apresentação do Programa",
                         "Este programa automatiza a criação de documentos de cotação de insumos, gerando 'IN.pdf' com a IN e as cotações em anexo, 'sga.txt' com as informações para inserir no SGA e 'data.txt' com todos os dados inseridos para importar novamente no programa em caso de algum ajuste."),
                        ("Como Usar",
                         "1. Preencha os dados do insumo, item e unidade no topo.\n2. Preencha os dados de cada fornecedor.\n3. Arraste e solte OU clique em 'Procurar...' para adicionar os arquivos de cotação.\n4. Especifique o diretório de saída.\n5. Clique em 'CRIAR DOCUMENTO FINAL' para iniciar o processo."),
                        ("Dicas",
                         "• O botão 'Limpar Cache' serve para apagar arquivos temporários que podem ter sido deixados para trás se o programa fechar inesperadamente.\n• O programa exporta um arquivo de nome 'data.txt', utilize o botão ‘Importar’ e selecione o arquivo 'data.txt' do item de sua escolha para trazer todos os dados automaticamente."),
                        ("Sobre",
                         "Em caso de falhas ou possíveis melhorias contatar no Teams (Higor Eduardo Marques). O código fonte está disponível em um repositório no github: Higor0227/Conversor-SOC")]
        for title, text in help_content:
            ttk.Label(help_win, text=title, font=(FONT_FAMILY, FONT_SIZE_BOLD)).pack(anchor='w', pady=(15, 2), padx=15)
            ttk.Label(help_win, text=text, wraplength=420, justify='left').pack(anchor='w', pady=(0, 10), padx=15)
        help_win.wait_window()

    def _collect_data_for_processing(self):
        def get_val(widget):
            if hasattr(widget, 'get_content'): return widget.get_content()
            return widget.get()

        def get_numeric(widget):
            val = get_val(widget)
            return val.replace(',', '.') if val else ""

        unidade_selecionada = get_val(self.unidade_entry)
        if unidade_selecionada == "Outro":
            unidade_final = get_val(self.unidade_outro_entry)
        else:
            unidade_final = unidade_selecionada

        data_package = {"insumo": get_val(self.insumo_entry), "item_num": get_val(self.item_num_entry),
                        "unidade": unidade_final,
                        "png_status": self.png_conversion_status,
                        "fornecedores_data": []}

        for i in range(3):
            widgets = self.supplier_widgets_list[i]
            if get_val(widgets['valor_insumo']):
                supplier_info = {"nome": get_val(widgets['fornecedor']), "data_str": get_val(widgets['data']),
                                 "valor_str": get_numeric(widgets['valor_insumo']),
                                 "frete_tipo": get_val(widgets['frete_combo']),
                                 "frete_valor_str": get_numeric(widgets['valor_frete_entry']),
                                 "mo_tipo": get_val(widgets['mo_combo']),
                                 "mo_valor_str": get_numeric(widgets['valor_mo_entry']),
                                 "fonte_str": get_val(widgets['fonte_entry']),
                                 "arquivo_path_raw": get_val(widgets['file_path_var']), }
                data_package["fornecedores_data"].append(supplier_info)
        return data_package


if __name__ == '__main__':
    root = TkinterDnD.Tk()
    root.iconbitmap(resource_path("logo.ico"))
    app = MainApplication(root)

    root.mainloop()