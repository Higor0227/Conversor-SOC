import os
import statistics as stc
from datetime import datetime
import pypdf
from weasyprint import HTML, CSS
import re
import pyperclip
import time
import sys

# Renomeado para maior clareza sobre sua função
class DocumentProcessor:
    def __init__(self, app_base_path, output_target_directory, structured_gui_data):
        """
        Inicializa o processador com dados puros.

        Args:
            app_base_path (str): O caminho onde os templates (e.g., 'template.html') estão.
            output_target_directory (str): O diretório onde os arquivos finais serão salvos.
            structured_gui_data (dict): O dicionário contendo todos os valores da UI.
        """
        # Armazena caminhos e dados
        self.app_path = app_base_path
        self.output_dir = output_target_directory
        self.data = structured_gui_data

        # Extrai dados do dicionário para atributos da instância
        self.item_num = self.data['item_num']
        self.insumo = self.data['insumo']
        self.unidade = self.data['unidade']
        self.png_conversion_status = self.data['png_status']
        self.fornecedores = self.data['fornecedores_data']

        # Calcula a lista de valores numéricos
        self.numeros = []
        for f_data in self.fornecedores:
            try:
                # Ensure 'valor_str' exists and is not None before conversion
                valor_str = f_data.get('valor_str')
                if valor_str:
                    self.numeros.append(float(valor_str))
                # else:
                #    print(f"Aviso: Fornecedor {f_data.get('nome', 'Desconhecido')} sem 'valor_str'.") # Optional: log missing values
            except (ValueError, TypeError) as e:
                # This case should ideally be handled/logged if a value is expected but invalid
                print(
                    f"Aviso: Valor inválido para fornecedor {f_data.get('nome', 'Desconhecido')}: '{f_data.get('valor_str')}'. Erro: {e}")
                continue

        # Atributos que serão calculados pelos métodos
        self.media = None
        self.mediana = None
        self.menor = None
        self.desvpad = None
        self.coefvaria = None
        self.liminf = None
        self.limsup = None
        self.valor_final_formatado = ""
        self.fonte_final = ""
        self.data_mais_recente = ""
        self.initial_pdf_from_html_path = ""  # Path to PDF generated from HTML

    def execute(self):
        """Executa o fluxo de trabalho: estatísticas, HTML->PDF, merge PDF, e TXT."""
        if not self.numeros:  # Check if any valid numbers were extracted
            print("Erro: Nenhum valor numérico válido de fornecedor para processar.")
            raise ValueError("Nenhum valor numérico válido de fornecedor para processar.")

        try:
            self._calculate_statistics()
            self._prepare_datas_e_fontes()
            self._edit_html_and_convert_to_pdf()  # Can raise exceptions
            self._merge_pdfs()  # Can raise exceptions
            self._save_summary_txt()
            print("Processo DocumentProcessor concluído com sucesso.")
        except FileNotFoundError as e:
            print(f"Erro crítico no DocumentProcessor: Arquivo essencial não encontrado - {e}")
            raise
        except pypdf.errors.PyPdfError as e:  # Corrected exception type
            print(f"Erro crítico no DocumentProcessor relacionado ao PDF (pypdf): {e}")
            raise
        except Exception as e:
            print(f"Ocorreu um erro inesperado durante a execução do DocumentProcessor: {e}")
            import traceback
            print(traceback.format_exc())
            raise

    def _calculate_statistics(self):
        if not self.numeros:
            print("Aviso: Tentativa de calcular estatísticas sem números válidos.")
            self.media = self.mediana = self.menor = self.desvpad = self.coefvaria = self.liminf = self.limsup = 0.0
            self.valor_final_formatado = "N/A"
            return

        if len(self.numeros) == 1:
            self.media = self.numeros[0]
            self.mediana = self.numeros[0]
            self.menor = self.numeros[0]
            self.desvpad = 0.0
            self.liminf = self.numeros[0]
            self.limsup = self.numeros[0]
            self.coefvaria = 0.0
        else:
            self.media = stc.mean(self.numeros)
            self.mediana = stc.median(self.numeros)
            self.menor = min(self.numeros)
            try:
                self.desvpad = stc.stdev(self.numeros)
            except stc.StatisticsError:
                self.desvpad = 0.0
            self.coefvaria = self.desvpad / self.media if self.media != 0 else 0
            self.liminf = self.media - self.desvpad
            self.limsup = self.media + self.desvpad

        final_value_numeric = self.media if self.coefvaria < 0.25 else self.mediana
        self.valor_final_formatado = f"{final_value_numeric:.2f}".replace(".", ",")

    def _prepare_datas_e_fontes(self):
        """Processa as datas e as fontes para uso posterior."""
        datas_validas = []
        fontes_parts = []
        for f_data in self.fornecedores:
            nome_fornecedor = f_data.get('nome', 'Fornecedor Desconhecido')
            fonte_fornecedor = f_data.get('fonte_str', 'Fonte não especificada')
            fontes_parts.append(f"{nome_fornecedor}: {fonte_fornecedor}")

            data_str_fornecedor = f_data.get('data_str')
            if data_str_fornecedor:
                try:
                    datas_validas.append(datetime.strptime(data_str_fornecedor, "%d/%m/%Y"))
                except ValueError:
                    print(f"Aviso: Data em formato inválido ignorada para {nome_fornecedor}: {data_str_fornecedor}")
                    continue

        self.fonte_final = "\n".join(fontes_parts)
        self.data_mais_recente = max(datas_validas).strftime('%d/%m/%Y') if datas_validas else "Nenhuma data válida"

    def resource_path(self, rel_path):
        """Retorna o caminho absoluto, mesmo dentro do .exe"""
        try:
            base_path = sys._MEIPASS  # se estiver empacotado
        except Exception:
            base_path = os.path.abspath(".")  # modo normal

        return os.path.join(base_path, rel_path)

    def _edit_html_and_convert_to_pdf(self):
        """Converte o template HTML preenchido para um arquivo PDF usando WeasyPrint."""
        html_path = self.resource_path("template.html")

        self.initial_pdf_from_html_path = os.path.join(self.app_path, 'saida_from_html.pdf')

        try:
            with open(html_path, 'r', encoding='utf-8') as template_file:
                html_template = template_file.read()
        except FileNotFoundError:
            print(
                f"Erro Crítico: O arquivo de template HTML '{html_path}' não foi encontrado em '{self.app_path}'.")
            raise

        html_export = html_template

        media_str = f"{self.media:.2f}".replace(".", ",") if self.media is not None else "N/A"
        mediana_str = f"{self.mediana:.2f}".replace(".", ",") if self.mediana is not None else "N/A"
        menor_str = f"{self.menor:.2f}".replace(".", ",") if self.menor is not None else "N/A"
        desvpad_str = f"{self.desvpad:.2f}".replace(".", ",") if self.desvpad is not None else "N/A"
        coefvaria_perc_str = f"{self.coefvaria * 100:.0f}%" if self.coefvaria is not None else "N/A"
        liminf_str = f"{self.liminf:.2f}".replace(".", ",") if self.liminf is not None else "N/A"
        limsup_str = f"{self.limsup:.2f}".replace(".", ",") if self.limsup is not None else "N/A"

        verif_coef_str = "N/A"
        mensagem_hetero_str = ""
        if self.coefvaria is not None:
            verif_coef_str = "Homogêneo" if self.coefvaria < 0.25 else "Heterogêneo"
            if self.coefvaria >= 0.25:
                mensagem_hetero_str = "Adotou-se a mediana dos preços pois conforme a IN 01/2021 Artigo 6º e § 2º.<br>A mediana será utilizada preferencialmente quando os preços coletados na pesquisa forem heterogêneos."

        valor_final_str = self.valor_final_formatado

        replacements = {
            "ITEM_NUM": self.item_num or "N/A",
            "ITEM_NAME": (self.insumo or "N/A").capitalize(),
            "ITEM_UNITY": self.unidade or "N/A",
            "VALOR_FINAL": valor_final_str,
            "MEDIA": media_str,
            "MEDIANA": mediana_str,
            "MENOR": menor_str,
            "DESVPAD": desvpad_str,
            "COEFVARIA": coefvaria_perc_str,
            "VERIF_COEF": verif_coef_str,
            "MENSAGEM_HETERO": mensagem_hetero_str,
            "LIMINF": liminf_str,
            "LIMSUP": limsup_str,
        }

        for key, value in replacements.items():
            html_export = re.sub(r"\{\{\s*" + re.escape(key) + r"\s*\}\}", str(value), html_export)

        max_fornecedores_in_template = 3
        for i in range(max_fornecedores_in_template):
            if i < len(self.fornecedores):
                f_data = self.fornecedores[i]
                nome_forn = f_data.get('nome', 'N/A').capitalize()
                data_forn = f_data.get('data_str', 'N/A')

                valor_forn_str = "N/A"
                if i < len(self.numeros) and self.numeros[i] is not None:
                    valor_forn_str = f"{self.numeros[i]:.2f}".replace(".", ",")
                elif f_data.get('valor_str'):
                    try:
                        valor_forn_str = f"{float(f_data.get('valor_str')):.2f}".replace(".", ",")
                    except:
                        valor_forn_str = f_data.get('valor_str', 'N/A')

                frete_tipo = f_data.get('frete_tipo', '-')
                frete_valor_str = f_data.get('frete_valor_str', '0.00')
                frete_display = (
                    f"R$ {frete_valor_str}".replace(".", ",") if frete_tipo == "Valor" else frete_tipo
                )

                mo_tipo = f_data.get('mo_tipo', '-')
                mo_valor_str = f_data.get('mo_valor_str', '0.00')
                mo_display = (
                    f"R$ {mo_valor_str}".replace(".", ",") if mo_tipo == "Sim" else
                    "Mão de obra inclusa" if mo_tipo == "Mão de obra inclusa" else "-"
                )
                fornecedor_tags = {
                    f"FORN_{i}": nome_forn, f"DATA_{i}": data_forn,
                    f"VALOR_FORN_{i}": valor_forn_str,
                    f"FRETE_VALOR_{i}": frete_display,
                    f"MO_{i}": mo_display,
                }
            else:
                fornecedor_tags = {
                    f"FORN_{i}": "-", f"DATA_{i}": "-", f"VALOR_FORN_{i}": "-",
                    f"FRETE_VALOR_{i}": "-", f"MO_{i}": "-",
                }

            for tag, value in fornecedor_tags.items():
                html_export = re.sub(r"\{\{\s*" + re.escape(tag) + r"\s*\}\}", str(value), html_export)

        try:
            HTML(string=html_export).write_pdf(self.initial_pdf_from_html_path)
            print(f"PDF gerado a partir do HTML salvo em: {self.initial_pdf_from_html_path}")
        except Exception as e:
            print(f"Erro Crítico: Falha ao gerar PDF a partir do HTML com WeasyPrint - {e}")
            if os.path.exists(self.initial_pdf_from_html_path):
                try:
                    os.remove(self.initial_pdf_from_html_path)
                except OSError:
                    pass
            raise

    def _merge_pdfs(self):
        """Mescla o PDF gerado pelo HTML com os PDFs dos anexos usando pypdf.PdfWriter."""
        processed_initial_pdf_path = os.path.join(self.app_path, 'processed_initial_from_html.pdf')
        final_pdf_path = os.path.join(self.output_dir, 'in.pdf')

        files_to_cleanup = [
            self.initial_pdf_from_html_path,
            processed_initial_pdf_path
        ]

        # Use PdfWriter for merging
        pdf_merger = pypdf.PdfWriter()

        try:
            if not os.path.exists(self.initial_pdf_from_html_path):
                print(
                    f"Erro Crítico: O arquivo PDF base '{self.initial_pdf_from_html_path}' não foi encontrado. Interrompendo a mesclagem.")
                raise FileNotFoundError(f"Arquivo PDF base '{self.initial_pdf_from_html_path}' não encontrado.")

            # Process the initial PDF (remove second page)
            reader_initial = pypdf.PdfReader(self.initial_pdf_from_html_path)
            writer_processed_initial = pypdf.PdfWriter()

            if len(reader_initial.pages) > 0:
                for i, page in enumerate(reader_initial.pages):
                    if i != 1:  # Skip second page (0-indexed)
                        writer_processed_initial.add_page(page)

            if len(writer_processed_initial.pages) == 0 and len(reader_initial.pages) > 0:
                print(
                    f"Aviso: O PDF '{self.initial_pdf_from_html_path}' resultou em 0 páginas após a remoção da página. Verifique o PDF original.")

            with open(processed_initial_pdf_path, 'wb') as f_out:
                writer_processed_initial.write(f_out)
            writer_processed_initial.close()  # Close this writer

            # Append the processed initial PDF to the main merger
            if os.path.exists(processed_initial_pdf_path) and os.path.getsize(processed_initial_pdf_path) > 0:
                try:
                    # Validate by trying to read it (optional, as PdfWriter.append can also fail)
                    # with open(processed_initial_pdf_path, 'rb') as f_val: pypdf.PdfReader(f_val)
                    pdf_merger.append(processed_initial_pdf_path)
                except pypdf.errors.PdfReadError:
                    print(
                        f"Aviso: O arquivo processado '{processed_initial_pdf_path}' não pôde ser lido como PDF. Não será adicionado.")
                except pypdf.errors.PyPdfError as e:
                    print(
                        f"Aviso: Erro PyPDF ao tentar adicionar '{processed_initial_pdf_path}' ao merge: {e}. Ignorado.")
                except Exception as e:
                    print(
                        f"Aviso: Erro genérico ao tentar adicionar '{processed_initial_pdf_path}' ao merge: {e}. Ignorado.")
            elif os.path.exists(processed_initial_pdf_path):
                print(f"Aviso: O arquivo '{processed_initial_pdf_path}' está vazio. Não será adicionado ao merge.")

            # Append attachment PDFs
            for i, f_data in enumerate(self.fornecedores):
                path_to_append = None
                png_stat_for_item = 0
                if i < len(self.png_conversion_status):
                    png_stat_for_item = self.png_conversion_status[i]

                if png_stat_for_item == 1:
                    img_pdf_name = f"image{i + 1}.pdf"
                    path_to_append = os.path.join(self.app_path, img_pdf_name)
                else:
                    raw_path = f_data.get("arquivo_path_raw")
                    if raw_path:
                        path_to_append = raw_path.translate({ord("{"): None, ord("}"): None})

                if path_to_append and os.path.exists(path_to_append):
                    try:
                        # with open(path_to_append, 'rb') as f_attach_val: pypdf.PdfReader(f_attach_val)
                        pdf_merger.append(path_to_append)
                        print(f"Anexado: {path_to_append}")
                    except pypdf.errors.PdfReadError:
                        print(
                            f"Aviso: Arquivo de anexo '{path_to_append}' não é um PDF válido ou está corrompido. Ignorado.")
                    except pypdf.errors.PyPdfError as e:
                        print(f"Erro PyPDF ao tentar anexar '{path_to_append}': {e}. Ignorado.")
                    except Exception as e:
                        print(f"Erro genérico ao tentar anexar '{path_to_append}': {e}. Ignorado.")
                elif path_to_append:
                    print(f"Aviso: Arquivo de anexo não encontrado e ignorado: {path_to_append}")

            # Write the final merged PDF
            if len(pdf_merger.pages) > 0:  # Check if PdfWriter has pages (indirectly)
                # PdfWriter doesn't have a direct .pages attribute like PdfMerger did.
                # We assume if appends were successful, it's ready to write.
                # A more robust check might involve trying to read the output stream
                # or checking if any append operations actually added pages.
                # For now, we'll rely on the fact that if appends happened, it should write.
                with open(final_pdf_path, "wb") as f_final:
                    pdf_merger.write(f_final)
                print(f"PDF final salvo em: {final_pdf_path}")
            else:
                # This condition might be harder to hit accurately with PdfWriter without inspecting its internal state.
                # If no files were successfully appended, the output PDF might be empty or just the initial PDF.
                print(
                    "Aviso/Erro: Nenhum documento adicional foi anexado ou o PDF base estava vazio. Verifique o resultado 'in.pdf'.")
                # Still try to write, it might be just the initial PDF if no attachments were valid
                with open(final_pdf_path, "wb") as f_final:
                    pdf_merger.write(f_final)
                if not os.path.getsize(final_pdf_path) > 0:
                    print("Erro Crítico: O arquivo 'in.pdf' está vazio ou não foi gerado.")


        except pypdf.errors.PyPdfError as e:
            print(f"Erro de PDF (pypdf) durante a mesclagem: {e}. O PDF pode estar corrompido.")
            raise
        except Exception as e:
            print(f"Ocorreu um erro inesperado durante a mesclagem de PDFs: {e}")
            raise
        finally:
            if pdf_merger:
                try:
                    pdf_merger.close()
                except Exception as e:
                    print(f"Aviso: Erro ao fechar o PdfWriter (merger): {e}")

            for fpath in files_to_cleanup:
                if os.path.exists(fpath):
                    try:
                        os.remove(fpath)
                    except OSError as e:
                        print(f"Aviso: Não foi possível remover o arquivo temporário {fpath}: {e}")

    def _save_summary_txt(self):
        """Salva um resumo em TXT e copia dados para o clipboard."""
        txt_filename = 'sga.txt'
        data_output_filename = 'data.txt'
        data_output_path = os.path.join(self.output_dir, data_output_filename)

        txt_path = os.path.join(self.output_dir, txt_filename)
        final_pdf_path_in_txt = os.path.join(self.output_dir, "in.pdf")

        valor_final = self.valor_final_formatado if self.valor_final_formatado is not None else "N/A"
        data_recente = self.data_mais_recente if self.data_mais_recente is not None else "N/A"
        fonte_final_str = self.fonte_final if self.fonte_final is not None else "N/A"

        try:
            pyperclip.copy(final_pdf_path_in_txt);
            time.sleep(0.3)
            pyperclip.copy(valor_final);
            time.sleep(0.3)
            pyperclip.copy(data_recente);
            time.sleep(0.3)
            pyperclip.copy(fonte_final_str)
            print("Dados copiados para o clipboard (caminho PDF, valor, data, fontes).")
        except pyperclip.PyperclipException as e:
            print(f"Aviso: Falha ao interagir com o clipboard: {e}")

        content_parts = [
            valor_final, data_recente,
            fonte_final_str.replace("\n", " | "),
            final_pdf_path_in_txt
        ]
        content = ";".join(content_parts)

        csv_data = []

        a = 2

        for f_data in enumerate(self.fornecedores):
            print(f_data)

        try:
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(content)
            with open(data_output_path, 'w', encoding='utf-8') as d:
                d.write(str(self.data))

        except IOError as e:
            print(f"Erro ao salvar o arquivo de resumo TXT '{txt_path}': {e}")