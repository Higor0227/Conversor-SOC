import os
import sys
import re
import locale
import statistics as stc
from datetime import datetime
import time
import pyperclip
import pypdf
from weasyprint import HTML


class DocumentProcessor:
    """
    Processa os dados da interface para calcular estatísticas, gerar, mesclar
    e salvar os documentos finais (IN.pdf, sga.txt, data.txt).
    """

    def __init__(self, app_base_path: str, output_target_directory: str, structured_gui_data: dict):
        """
        Inicializa o processador com os caminhos e os dados estruturados da UI.
        """
        # --- Configuração de Caminhos e Dados ---
        self.app_path = app_base_path
        self.output_dir = output_target_directory
        self.data = structured_gui_data

        # --- Desempacotamento de Dados Principais ---
        self.item_num = self.data.get('item_num', '')
        self.insumo_de_marca = self.data.get('insumo_de_marca', '')
        self.insumo = self.data.get('insumo', '')
        self.unidade = self.data.get('unidade', '')
        self.fornecedores = self.data.get('fornecedores_data', [])

        # --- Inicialização de Atributos Calculados ---
        self.media = self.mediana = self.menor = self.desvpad = self.coefvaria = None
        self.liminf = self.limsup = None
        self.valor_final_formatado = ""
        self.fonte_final = ""
        self.data_mais_recente_str = ""

        # --- ETAPA DE LIMPEZA E PREPARAÇÃO DOS DADOS ---
        self._setup_locale()
        # Converte todos os valores numéricos de string para float logo no início
        self.numeros = self._sanitize_and_extract_numeric_data()

    def execute(self) -> str:
        """
        Orquestra o fluxo completo de processamento de documentos.
        Retorna o caminho do diretório de saída em caso de sucesso.
        """
        if not self.numeros or all(v == 0 for v in self.numeros):
            raise ValueError("Nenhum valor numérico válido de fornecedor para processar.")

        try:
            # 1. Realiza cálculos estatísticos.
            self._calculate_statistics()

            # 2. Prepara os metadados (fontes, datas).
            self._process_supplier_metadata()

            # 3. Prepara o dicionário de contexto para o template.
            context = self._prepare_template_context()

            # 4. Renderiza o HTML para um PDF inicial.
            initial_pdf_path = self._render_html_to_pdf(context)

            # 5. Mescla o PDF inicial com os anexos.
            self._merge_all_pdfs(initial_pdf_path)

            # 6. Salva os arquivos de resumo.
            self._save_summary_files()

            return self.output_dir

        except Exception as e:
            print(f"Ocorreu um erro crítico durante a execução do DocumentProcessor: {e}")
            import traceback
            traceback.print_exc()
            raise

    # --- Métodos de Preparação e Cálculo ---

    def _clean_and_convert_to_float(self, num_str: str | None) -> float:
        """
        Converte de forma segura uma string numérica do formato BR para um float.
        Trata strings vazias ou nulas como 0.0.
        """
        if not num_str:
            return 0.0
        try:
            # Converte de "1.234,56" para "1234.56"
            standard_format_str = num_str.replace('.', '').replace(',', '.')
            return float(standard_format_str)
        except (ValueError, TypeError):
            print(f"Aviso: Não foi possível converter a string '{num_str}' para um número. Usando valor 0.0.")
            return 0.0

    def _sanitize_and_extract_numeric_data(self) -> list[float]:
        """
        Itera sobre os fornecedores para converter todos os valores em string (valor, frete, mo)
        para float, armazenando-os para uso posterior e retornando a lista de valores principais.
        """
        numeros_extraidos = []
        for f_data in self.fornecedores:
            # Converte o valor principal e o adiciona à lista de números para estatística
            valor_principal_float = self._clean_and_convert_to_float(f_data.get('valor_str'))
            numeros_extraidos.append(valor_principal_float)

            # Adiciona os valores convertidos de volta ao dicionário para fácil acesso
            f_data['valor_float'] = valor_principal_float
            f_data['frete_float'] = self._clean_and_convert_to_float(f_data.get('frete_valor_str'))
            f_data['mo_float'] = self._clean_and_convert_to_float(f_data.get('mo_valor_str'))

        return numeros_extraidos

    def _calculate_statistics(self):
        """Calcula as principais métricas estatísticas com base nos valores extraídos."""
        # Filtra valores zero que podem ter vindo de campos vazios
        numeros_validos = [n for n in self.numeros if n > 0]
        if not numeros_validos:
            raise ValueError("Após a limpeza, não restaram valores maiores que zero para calcular estatísticas.")

        if len(numeros_validos) == 1:
            self.media = self.mediana = self.menor = self.liminf = self.limsup = numeros_validos[0]
            self.desvpad = self.coefvaria = 0.0
        else:
            self.media = stc.mean(numeros_validos)
            self.mediana = stc.median(numeros_validos)
            self.menor = min(numeros_validos)
            try:
                self.desvpad = stc.stdev(numeros_validos)
            except stc.StatisticsError:
                self.desvpad = 0.0

            self.coefvaria = (self.desvpad / self.media) if self.media != 0 else 0
            self.liminf = self.media - self.desvpad
            self.limsup = self.media + self.desvpad

        # A decisão do valor final (média ou mediana) baseia-se no coeficiente de variação.
        valor_final_numerico = self.media if self.coefvaria < 0.25 else self.mediana
        self.valor_final_formatado = self._format_currency(valor_final_numerico)

    def _process_supplier_metadata(self):
        """Processa e formata as datas e fontes dos fornecedores."""
        datas_validas = []
        fontes_parts = []
        for f_data in self.fornecedores:
            # Processa apenas se o fornecedor tiver um valor válido
            if f_data.get('valor_float', 0) > 0:
                nome = f_data.get('nome', 'Fornecedor Desconhecido')
                fonte = f_data.get('fonte_str', 'Fonte não especificada')
                fontes_parts.append(f"{nome}: {fonte}")

                data_str = f_data.get('data_str')

                if data_str:
                    datas_validas.append(datetime.strptime(data_str, "%d/%m/%Y"))

        self.fonte_final = "\n".join(fontes_parts)
        self.data_mais_recente_str = min(datas_validas).strftime('%d/%m/%Y')


    # --- Métodos de Geração de PDF ---

    def _prepare_template_context(self) -> dict:
        """Cria um dicionário (contexto) com todos os dados formatados para o template HTML."""
        context = {
            "ITEM_NUM": self.item_num or "N/A",
            "ITEM_NAME": (self.insumo or "N/A").capitalize(),
            "ITEM_UNITY": self.unidade or "N/A",
            "VALOR_FINAL": self.valor_final_formatado,
            "MEDIA": self._format_currency(self.media),
            "MEDIANA": self._format_currency(self.mediana),
            "MENOR": self._format_currency(self.menor),
            "DESVPAD": self._format_currency(self.desvpad),
            "COEFVARIA": f"{self.coefvaria * 100:.0f}%" if self.coefvaria is not None else "N/A",
            "LIMINF": self._format_currency(self.liminf),
            "LIMSUP": self._format_currency(self.limsup)
        }


        if self.coefvaria is not None:
            context["VERIF_COEF"] = "Homogêneo" if self.coefvaria < 0.25 else "Heterogêneo"
            if not self.insumo_de_marca:
                context[
                    "MENSAGEM_HETERO"] = "Adotou-se a mediana dos preços pois, conforme a IN 01/2021 Artigo 6º e § 2º, a mediana será utilizada preferencialmente quando os preços coletados na pesquisa forem heterogêneos." if self.coefvaria >= 0.25 else ""

            context["BORDA"] = "red-border" if self.coefvaria >= 0.25 else "no-border"

        for i in range(3):
            if i < len(self.fornecedores) and self.fornecedores[i].get('valor_float', 0) > 0:
                f_data = self.fornecedores[i]

                if i == 0:
                    if self.insumo_de_marca:
                        context[
                            "MENSAGEM_HETERO"] = f"Adotou-se o preço do fornecedor {f_data.get('nome', 'N/A').capitalize()} por se tratar da marca especificada para o item no memorial. "
                        context["VALOR_FINAL"] = self._format_currency(f_data['valor_float'])

                        context["BORDA"] = "red-border"

                context[f"FORN_{i}"] = f_data.get('nome', 'N/A').capitalize()

                context[f"DATA_{i}"] = f_data.get('data_str', 'N/A')
                context[f"VALOR_FORN_{i}"] = self._format_currency(f_data['valor_float'])
                context[f"FRETE_VALOR_{i}"] = self._format_display_value(f_data, 'frete')
                context[f"MO_{i}"] = self._format_display_value(f_data, 'mo')
            else:
                for key in ["FORN", "DATA", "VALOR_FORN", "FRETE_VALOR", "MO"]:
                    context[f"{key}_{i}"] = "-"
        return context

    def _render_html_to_pdf(self, context: dict) -> str:
        html_template_path = self._resource_path("template.html")
        output_pdf_path = os.path.join(self.app_path, "temp_from_html.pdf")
        with open(html_template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        for key, value in context.items():
            html_content = re.sub(r"\{\{\s*" + re.escape(key) + r"\s*\}\}", str(value), html_content)
        HTML(string=html_content).write_pdf(output_pdf_path)
        return output_pdf_path

    def _merge_all_pdfs(self, initial_pdf_path: str):
        final_pdf_path = os.path.join(self.output_dir, "in.pdf")
        merger = pypdf.PdfWriter()
        try:
            reader = pypdf.PdfReader(initial_pdf_path)
            if reader.pages:
                merger.add_page(reader.pages[0])
            attachment_paths = []
            for f_data in self.fornecedores:
                for key in ["arquivo_path_raw", "arquivo_2_path_raw"]:
                    path = f_data.get(key)
                    if path and os.path.exists(path):
                        attachment_paths.append(path)
                    elif path:
                        print(f"Aviso: Anexo não encontrado e ignorado: {path}")
            self._append_attachments(merger, attachment_paths)
            with open(final_pdf_path, "wb") as f_out:
                merger.write(f_out)
        finally:
            merger.close()
            if os.path.exists(initial_pdf_path):
                os.remove(initial_pdf_path)

    def _append_attachments(self, merger: pypdf.PdfWriter, paths: list[str]):
        for path in paths:
            try:
                merger.append(path)
            except Exception as e:
                print(f"Aviso: Falha ao anexar '{path}'. Erro: {e}")

    # --- Métodos de Salvamento e Utilitários ---

    def _save_summary_files(self):
        sga_path = os.path.join(self.output_dir, 'sga.txt')
        data_path = os.path.join(self.output_dir, 'data.txt')
        final_pdf_path = os.path.join(self.output_dir, "in.pdf")
        sga_content = ";".join([
            self.valor_final_formatado,
            self.data_mais_recente_str,
            self.fonte_final.replace("\n", " | "),
            final_pdf_path
        ])

        copy = [self.valor_final_formatado,
            self.data_mais_recente_str,
            self.fonte_final.replace("\n", " | "),
            final_pdf_path]
        try:
            with open(sga_path, 'w', encoding='utf-8') as f:
                f.write(sga_content)
            with open(data_path, 'w', encoding='utf-8') as f:
                f.write(str(self.data))
        except IOError as e:
            print(f"Erro ao salvar arquivos de resumo: {e}")
        try:
            for item in copy:
                pyperclip.copy(item)
                time.sleep(0.3)

            print("Dados para SGA copiados para a área de transferência.")
        except pyperclip.PyperclipException as e:
            print(f"Aviso: Falha ao acessar a área de transferência: {e}")

    @staticmethod
    def _setup_locale():
        try:
            locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
        except locale.Error:
            print("Aviso: Localidade 'pt_BR.UTF-8' não encontrada. Usando o padrão do sistema.")
            locale.setlocale(locale.LC_ALL, '')

    @staticmethod
    def _format_currency(value) -> str:
        if value is None or not isinstance(value, (int, float)): return "N/A"
        return locale.format_string('%.2f', value, grouping=True)

    def _format_display_value(self, f_data, key: str) -> str:
        """Formata um valor para exibição (frete, mão de obra) usando os valores float já convertidos."""
        tipo = f_data.get(f'{key}_tipo', '-')
        valor_float = f_data.get(f'{key}_float', 0.0)

        if tipo in ['Valor', 'Sim']:
            return f"R$ {self._format_currency(valor_float)}" if valor_float > 0 else tipo

        return tipo if tipo != '-' else "-"

    def _resource_path(self, rel_path: str) -> str:
        try:
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, rel_path)