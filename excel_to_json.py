import pandas as pd
from file_processing import DocumentProcessor

itens = pd.read_csv('itens.csv')


datas = []

for index, row in itens.iterrows():

    data_package = {
                "insumo": row['insumo'],
                "item_num": row['item_num'],
                "unidade": row['unidade'],
                "output_directory": row['output_directory'],
                "fornecedores_data": []
            }

    for i in range(1, 4):
        print(row['output_directory'])
        supplier_info = {
                    "nome": row[f'nome_forn{i}'],
                    "data_str": row[f'data_forn{i}'],
                    "valor_str": row[f'valor_item_forn{i}'],
                    "frete_tipo": row[f'frete_tipo_forn{i}'],
                    "frete_valor_str": row[f'frete_valor_str_forn{i}'],
                    "mo_tipo": row[f'mo_tipo_forn{i}'],
                    "mo_valor_str": row[f'mo_valor_forn{i}'],
                    "fonte_str": row[f'fonte_forn{i}'],
                    "arquivo_path_raw": row[f'arquivo_path_raw_forn{i}'],
                    "arquivo_2_path_raw": row[f'arquivo_2_path_raw_forn{i}']
                        }

        data_package["fornecedores_data"].append(supplier_info)

    datas.append(data_package)

for item in datas:
    processor = DocumentProcessor(app_base_path='.',
                              output_target_directory='output', structured_gui_data=item)
    processor.execute()