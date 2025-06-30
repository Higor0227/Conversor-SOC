# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk
import locale

# --- Configuração da Localidade ---
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    print("Localidade 'pt_BR.UTF-8' não encontrada. Usando o padrão do sistema.")
    locale.setlocale(locale.LC_ALL, '')

# --- Constantes de Estilo ---
PLACEHOLDER_COLOR = '#A9A9A9'
ENTRY_BG_COLOR = '#4A4A4A'
ENTRY_FG_COLOR = '#FFFFFF'


class EntryWithPlaceholder(ttk.Entry):
    """
    Um widget Entry que suporta um texto de **placeholder** personalizável.
    """
    def __init__(self, master=None, placeholder="Placeholder", **kwargs):
        self.placeholder_style_name = f"placeholder.{id(self)}.TEntry"
        super().__init__(master, style='TEntry', **kwargs)
        self.placeholder = placeholder
        style = ttk.Style()
        style.configure(
            self.placeholder_style_name,
            foreground=PLACEHOLDER_COLOR,
            fieldbackground=ENTRY_BG_COLOR
        )
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)
        self.put_placeholder()

    def put_placeholder(self):
        if self.get(): return
        self.configure(style=self.placeholder_style_name)
        self.insert(0, self.placeholder)

    def _on_focus_in(self, event=None):
        if self.cget('style') == self.placeholder_style_name:
            self.delete(0, 'end')
            self.configure(style='TEntry')

    def _on_focus_out(self, event=None):
        if not self.get():
            self.put_placeholder()

    def get_content(self) -> str:
        if self.cget('style') == self.placeholder_style_name:
            return ""
        return self.get()

    def set_value(self, value: str):
        self._on_focus_in()
        self.delete(0, 'end')
        self.insert(0, str(value))
        if not str(value):
            self._on_focus_out()

    def clear(self):
        self.set_value("")


class NumberEntry(ttk.Entry):
    """
    Um widget Entry para números com formatação brasileira e placeholder.
    Versão final corrigida para o ciclo completo de Importar/Exportar.
    """
    def __init__(self, master=None, placeholder="Valor", **kwargs):
        self.placeholder = placeholder
        self.placeholder_style_name = f"placeholder.num.{id(self)}.TEntry"
        super().__init__(master, style='TEntry', **kwargs)
        style = ttk.Style()
        style.configure(
            self.placeholder_style_name,
            foreground=PLACEHOLDER_COLOR,
            fieldbackground=ENTRY_BG_COLOR
        )
        vcmd = (self.register(self._on_validate), '%P', '%S', '%d')
        self.configure(validate='key', validatecommand=vcmd)
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<KeyRelease>", self._format_on_key_release)
        self.put_placeholder()

    def put_placeholder(self):
        if self.get(): return
        self.configure(validate='none')
        self.configure(style=self.placeholder_style_name)
        self.insert(0, self.placeholder)
        self.configure(validate='key')

    def _on_focus_in(self, event=None):
        if self.cget('style') == self.placeholder_style_name:
            self.delete(0, 'end')
            self.configure(style='TEntry')

    def get_content(self) -> str:
        if self.cget('style') == self.placeholder_style_name: return ""
        return self.get()

    def _on_validate(self, new_value, char_inserted, action_code) -> bool:
        if action_code == '0': return True
        if not char_inserted.isdigit() and char_inserted != ',': return False
        if char_inserted == ',' and ',' in self.get(): return False
        return True

    def _format_on_key_release(self, event=None):
        if not event or event.keysym not in ('Key', 'BackSpace'): return
        if self.cget('style') == self.placeholder_style_name: return
        original_text = self.get()
        cursor_pos = self.index(tk.INSERT)
        parts = original_text.replace('.', '').split(',', 1)
        integer_part = parts[0]
        decimal_part = parts[1] if len(parts) > 1 else None
        if not integer_part: return
        try:
            formatted_integer = locale.format_string("%d", int(integer_part), grouping=True)
        except (ValueError, TypeError):
            return
        new_text = formatted_integer
        if decimal_part is not None: new_text += ',' + decimal_part
        if new_text != original_text:
            self.configure(validate='none')
            self.delete(0, tk.END)
            self.insert(0, new_text)
            self.configure(validate='key')
            new_cursor_pos = cursor_pos + (len(new_text) - len(original_text))
            self.icursor(new_cursor_pos)

    def _on_focus_out(self, event=None):
        content = self.get_content()
        if content:
            try:
                num_value = float(content.replace('.', '').replace(',', '.'))
                formatted_value = locale.format_string("%.2f", num_value, grouping=True)
                self.configure(validate='none')
                self.delete(0, tk.END)
                self.insert(0, formatted_value)
                self.configure(validate='key')
            except (ValueError, TypeError):
                self.delete(0, tk.END)
        if not self.get():
            self.put_placeholder()

    def set_value(self, value: str):
        """
        Define um valor programaticamente, formatando-o corretamente.
        Versão final robusta que desativa a validação durante a inserção.
        """
        self._on_focus_in()

        # Desativa a validação temporariamente para evitar conflitos
        self.configure(validate='none')

        self.delete(0, 'end')

        if value is not None and str(value).strip() != "":
            try:
                valor_str = str(value)
                string_limpa = valor_str.replace('.', '').replace(',', '.')
                num_value = float(string_limpa)
                formatted_value = locale.format_string("%.2f", num_value, grouping=True)
                self.insert(0, formatted_value)
            except (ValueError, TypeError):
                # Se algo der errado, certifica-se de que o campo fique vazio
                self.delete(0, 'end')

        # Se o campo acabou vazio por qualquer motivo, coloca o placeholder
        if not self.get():
            self.put_placeholder()

        # Reativa a validação
        self.configure(validate='key')

    def clear(self):
        self.set_value("")