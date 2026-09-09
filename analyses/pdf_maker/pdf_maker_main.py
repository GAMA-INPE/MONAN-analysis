
import pdf_maker_aux as pdf_aux
import pdf_maker_config as pdf_config

def main():

    print ("Creating folder structure...")
    pdf_aux.create_folder_structure()

    print ("Reading and preprocessing input data...")
    pdf_aux.read_and_preprocess_input_data()

    print ("Constructing and saving PDF...")
    pdf_aux.build_pdf()

    print ("Copying config file to output folder...")
    pdf_aux.cp_config_files()

    print ("Done.\n")
    print ("Output data can be found in: ", pdf_config.DIR_OUTPUT_DATA, "\n")
    print ("Output figs can be found in: ", pdf_config.DIR_OUTPUT_FIGS, "\n")

if __name__ == "__main__":
    main()