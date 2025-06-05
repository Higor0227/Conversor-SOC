import tkinter as tk
from tkinter import ttk
import uuid  # Usado para criar nomes de estilo únicos


class EntryWithPlaceholder(ttk.Entry):
    def __init__(self, master=None, placeholder="PLACEHOLDER",
                 color='#C0C0C0'):  # Cor padrão agora é um cinza mais claro
        # 1. Criar nomes de estilo únicos para esta instância específica
        self.normal_style_name = f"{uuid.uuid4()}.TEntry"
        self.placeholder_style_name = f"{uuid.uuid4()}.placeholder.TEntry"

        super().__init__(master, style=self.normal_style_name)

        self.placeholder = placeholder

        style = ttk.Style()

        # Copia o layout do TEntry padrão para os nossos novos estilos
        style.layout(self.normal_style_name, style.layout('TEntry'))
        style.layout(self.placeholder_style_name, style.layout('TEntry'))

        # Estilo para quando o usuário está digitando (texto branco, fundo normal)
        style.configure(self.normal_style_name,
                        foreground='white',
                        fieldbackground='#4A4A4A')  # Fundo padrão da entrada

        # Estilo para quando o placeholder está visível
        style.configure(self.placeholder_style_name,
                        foreground=color,  # Cor do texto do placeholder (agora mais clara)
                        fieldbackground='#404040')  # NOVO: Fundo mais escuro para o campo do placeholder

        # 3. Vincular os eventos
        self.bind("<FocusIn>", self.foc_in)
        self.bind("<FocusOut>", self.foc_out)

        self.put_placeholder()

    def put_placeholder(self):
        """Insere o texto do placeholder e aplica o estilo de placeholder."""
        if not self.get():
            self.insert(0, self.placeholder)
            # Aplica o estilo que tem a cor de texto cinza e o fundo escuro
            self.configure(style=self.placeholder_style_name)

    def foc_in(self, *args):
        """Limpa o placeholder e aplica o estilo de texto normal."""
        # Se o estilo atual for o de placeholder, limpa e troca.
        if self.cget('style') == self.placeholder_style_name:
            self.delete(0, 'end')
            # Aplica o estilo que tem a cor de texto normal e o fundo padrão
            self.configure(style=self.normal_style_name)

    def foc_out(self, *args):
        """Recoloca o placeholder se o campo estiver vazio ao perder o foco."""
        if not self.get():
            self.put_placeholder()

    def get_content(self):
        """Metodo auxiliar para obter o valor real, ignorando o placeholder."""
        if self.cget('style') == self.placeholder_style_name:
            return ""
        return self.get()

    def set_value(self, value: str):
        """Define um valor real no campo, removendo o placeholder e aplicando o estilo normal."""
        self.configure(style=self.normal_style_name)
        self.delete(0, 'end')
        self.insert(0, value)
