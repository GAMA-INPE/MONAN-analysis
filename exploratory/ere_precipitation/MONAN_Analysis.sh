#!/bin/bash

exec > >(tee MONAN_Analysis_output.txt) 2>&1

##########################

#####  #####  #####  #####
#      #   #  # # #  #   #
# ###  #####  # # #  #####
#   #  #   #  # # #  #   #
#####  #   #  # # #  #   #

##########################
# Analysis scripts files #
##########################

PREC="MONAN_Prec.py"                    # MONAN_nc_24h_acum_newcolorbar.py
BIAS="MONAN_Bias.py"                    # Bias_MONAN_x_GPM_x_GSMAP_x_MSWEP.py
MAE="MONAN_Mae.py"                      # MAE_MONAN_x_GPM_x_GSMAP_x_MSWEP.py
SKILL="MONAN_Skill.py"                  # Skill_score_MONAN_x_GPM_x_GSMAP_x_MSWEP.py
MONTHLY_MEAN="MONAN_monthly_mean.sh"    # Gera_monthly_*.sh
MEAN_BIAS="MONAN_mean_Bias.py"          # Mean_Bias_MONAN_BAM_GFS.py
MEAN_MAE="MONAN_mean_Mae.py"            # Mean_MAE_MONAN_BAM_GFS.py
MEAN_RMSE="MONAN_mean_RMSE.py"          # Mean_RMSE_MONAN_BAM_GFS.py
MEAN_SKILL="MONAN_mean_Skill.py"        # Mean_Skill_score_MONAN_BAM_GFS.py
HEATMAP="MONAN_Heatmap.py"              # Plot_Series_Heatmap_skill_score_MONAN_BAM_GFS.py

#####################################################################
# Input and output directories                                      #
# NETCDF_PATH: Where the comparison NetCDF files are located        #
# MONAN_PATH: Where the MONAN simulation output files are located   #
# OUTPUT_PATH: Where the analysis results will be saved             #
# LISTA_PATH: Where the monthly mean lists will be saved            #
# PREFIXO_ARQ: Prefix for the MONAN output files                    #
# SUFIXO_ARQ: Suffix for the MONAN output files                     #
#####################################################################

NETCDF_PATH="/home2/eduardo.eras/workspace/NetCDFs/"
MONAN_PATH="/p/projetos/monan_atm/eduardo.eras/MONAN/scripts_CD-CT/dataout/"
OUTPUT_PATH="/home2/eduardo.eras/workspace/python/output/"
LISTA_PATH="/home2/eduardo.eras/workspace/python/listas_medias"
PREFIXO_ARQ="MONAN_DIAG_G_POS_GFS_"
SUFIXO_ARQ=".00.00.x655362L55.nc"

#####################################################################
# Erase old output files to avoid confusion (optional, be careful!) #
#####################################################################
rm -rf ${OUTPUT_PATH}/*
rm -rf ${LISTA_PATH}/*

##########################################################
# Date range for the simulations (Minimum range: 5 days) #
##########################################################

#Full range simulation
START_DATE="2025-12-01" 
END_DATE="2025-12-30"

#Short range simulation
#START_DATE="2025-12-10" 
#END_DATE="2025-12-19"

#Test simulation
#START_DATE="2025-12-10" 
#END_DATE="2025-12-11"

###################################################
# Simulation span in hours (e.g., 120 for 5 days) #
###################################################

LENGTH=120

####################################################
# Precipitation threshold for skill score analysis #
####################################################

THRESHOLD=(1 2 5 10 20 50)

######################################
# Analysis name for output directory #
######################################
ANALYSIS_NAME="30_days_mean" # e.g., "full_range", "short_test", etc.

##################################
# Generate Plot Maps?            #
# Set to 1 for True, 0 for False #
##################################
GENERATE_MAPS=0

####################################################
# Select Analysis to run (1 for True, 0 for False) #
####################################################
RUN_BASE_ANALYSIS=1
RUN_MONTHLY_ANALYSIS=1
RUN_MEAN_ANALYSIS=1
RUN_SKILL_ANALYSIS=1
RUN_HEATMAP_ANALYSIS=1

#################################################################################
#                                                                               #
#                           .,,uod8B8bou,,.                                     #
#                  ..,uod8BBBBBBBBBBBBBBBBRPFT?l!i:.                            #
#             ,=m8BBBBBBBBBBBBBBBRPFT?!||||||||||||||                           #
#             !...:!TVBBBRPFT||||||||||!!^^""'   ||||                           #
#             !.......:!?|||||!!^^""'            ||||                           #
#             !.........||||                     ||||                           #
#             !.........||||  ##                 ||||                           #
#             !.........||||                     ||||                           #
#             !.........||||                     ||||                           #
#             !.........||||                     ||||                           #
#             !.........||||                     ||||                           #
#             `.........||||                    ,||||                           #
#              .;.......||||               _.-!!|||||                           #
#       .,uodWBBBBb.....||||       _.-!!|||||||||!:'                            #
#    !YBBBBBBBBBBBBBBb..!|||:..-!!|||||||!iof68BBBBBb....                       #
#    !..YBBBBBBBBBBBBBBb!!||||||||!iof68BBBBBBRPFT?!::   `.                     #
#    !....YBBBBBBBBBBBBBBbaaitf68BBBBBBRPFT?!:::::::::     `.                   #
#    !......YBBBBBBBBBBBBBBBBBBBRPFT?!::::::;:!^"`;:::       `.                 #
#    !........YBBBBBBBBBBRPFT?!::::::::::^''...::::::;         iBBbo.           #
#    `..........YBRPFT?!::::::::::::::::::::::::;iof68bo.      WBBBBbo.         #
#      `..........:::::::::::::::::::::::;iof688888888888b.     `YBBBP^'        #
#        `........::::::::::::::::;iof688888888888888888888b.     `             #
#          `......:::::::::;iof688888888888888888888888888888b.                 #
#            `....:::;iof688888888888888888888888888888888899fT!                #
#              `..::!8888888888888888888888888888888899fT|!^"'                  #
#                `' !!988888888888888888888888899fT|!^"'                        #
#                    `!!8888888888888888899fT|!^"'                              #
#                      `!988888888899fT|!^"'                                    #
#                        `!9899fT|!^"'                                          #
#                          `!^"'                                                #
#                                                                               #  
#################################################################################

##################################
# Functions, Methods and Imports #
##################################

#Load CDO monule for data manipulation
module load cdo

#Function to print headers for better readability
print_header() {
    echo -e "\n################################################################"
    echo "$1"
    echo -e "################################################################\n"
}

print_status() {
    echo -e "\n----------------------------------------------------------------"
    echo "$1"
    echo -e "----------------------------------------------------------------\n"
}

base_analysis() {
    #Convert dates to Unix timestamps for looping
    start_ts=$(date -d "$START_DATE" +%s)
    end_ts=$(date -d "$END_DATE" +%s)

    #Looping over dates (the sane way)
    #Strategy: Convert dates to Unix timestamps (seconds since 1970-01-01),
    #loop numerically, them convert back to human dates.
    #This avoids calendar madness.
    for (( ts = start_ts; ts <= end_ts; ts += 86400 )); do

        #Get individual date elements
        year=$(date -d "@$ts" +%Y)
        month=$(date -d "@$ts" +%m)
        day=$(date -d "@$ts" +%d)
        hour=$(date -d "@$ts" +%H)

        simulation_date=$(date -d "@$ts" +%Y%m%d00)
        message="* * * Simulation for date: ${year} ${month} ${day} with span: $LENGTH hours * * *"
        print_header "$message"

        #Run the analysis scripts
        print_status "24 hours precipitation accumulation"
        python ${PREC} ${year} ${month} ${day} ${hour} ${LENGTH} ${MONAN_PATH} ${OUTPUT_PATH} ${PREFIXO_ARQ} ${SUFIXO_ARQ} ${GENERATE_MAPS}

        print_status "Bias analysis"
        python ${BIAS} ${year} ${month} ${day} ${hour} ${LENGTH} ${NETCDF_PATH} ${OUTPUT_PATH} ${GENERATE_MAPS}

        print_status "MAE analysis"
        python ${MAE} ${year} ${month} ${day} ${hour} ${LENGTH} ${NETCDF_PATH} ${OUTPUT_PATH} ${GENERATE_MAPS}

        print_status "Skill score analysis"
        for THR in "${THRESHOLD[@]}"; do
            print_status "Skill score analysis for threshold: ${THR} mm"
            python ${SKILL} ${year} ${month} ${day} ${hour} ${LENGTH} ${THR} ${NETCDF_PATH} ${OUTPUT_PATH}
        done

    done
}

monthly_analysis() {
    processes=("bias" "rmse" "skill")
    ini_valid=$(date -d "${START_DATE} 00:00" +%Y%m%d%H)
    fim_valid=$(date -d "${END_DATE} 23:00" +%Y%m%d%H)
    for proc in "${processes[@]}"; do
        print_status "Computing monthly mean for process: ${proc}"
        if [ "${proc}" == "skill" ]; then
            for THR in "${THRESHOLD[@]}"; do
                print_status "Computing monthly mean for skill score with threshold: ${THR} mm"
                bash ${MONTHLY_MEAN} ${ini_valid} ${fim_valid} ${proc} ${OUTPUT_PATH} ${ANALYSIS_NAME} ${THR}
            done
        else
            bash ${MONTHLY_MEAN} ${ini_valid} ${fim_valid} ${proc} ${OUTPUT_PATH} ${ANALYSIS_NAME} 
        fi
    done
}

mean_analysis() {
    print_status "Mean bias, MAE, RMSE and skill score across all lead times"
    ano=${START_DATE:0:4}
    mes=${START_DATE:5:2}
    dominio=(GLB AMS ACC)
    for dom in "${dominio[@]}"; do
        python ${MEAN_BIAS} ${ano} ${mes} ${dom} ${ANALYSIS_NAME} ${NETCDF_PATH} ${OUTPUT_PATH}
        python ${MEAN_MAE} ${ano} ${mes} ${dom} ${ANALYSIS_NAME} ${NETCDF_PATH} ${OUTPUT_PATH}
        python ${MEAN_RMSE} ${ano} ${mes} ${dom} ${ANALYSIS_NAME} ${NETCDF_PATH} ${OUTPUT_PATH}
    done
}

skill_analysis() {
    print_status "Mean skill score across all lead times for different thresholds"
    ano=${START_DATE:0:4}
    mes=${START_DATE:5:2}
    for THR in "${THRESHOLD[@]}"; do
        python ${MEAN_SKILL} ${ano} ${mes} ${THR} ${ANALYSIS_NAME} ${NETCDF_PATH} ${OUTPUT_PATH} ${GENERATE_MAPS}
    done
}

heatmap_analysis() {
    print_status "Generating heatmaps for skill scores"
    ano=${START_DATE:0:4}
    mes=${START_DATE:5:2}
    for reg in "GLB" "AMS" "ACC"; do
        python ${HEATMAP} ${ano} ${mes} ${reg} ${ANALYSIS_NAME} ${OUTPUT_PATH}
    done
}

#################################################################################
#                                                                               #
#                              Main analysis loop                               #
#                                                                               #
#################################################################################

print_header "* * *              MONAN Analysis starting...              * * *"

echo -e "\n##############################################"
echo "  _____   _______    ___    _____    _______  "
echo " / ____| |__   __|  /   \  |  __ \  |__   __| " 
echo "| (___      | |    /  ^  \ | |__) |    | |    "
echo " \___ \     | |   /  /_\  \|  _  /     | |    "
echo " ____) |    | |  /  _____  \ | \ \     | |    "
echo "|_____/     |_| /__/     \__\|  \_\    |_|    "
echo -e "##############################################\n"

# Record the start time for runtime calculation
START_TIME=$(date +%s)

# Run the analysis functions in sequence ###################################
if [ $RUN_BASE_ANALYSIS -eq 1 ]; then
    base_analysis
fi
if [ $RUN_MONTHLY_ANALYSIS -eq 1 ]; then
    monthly_analysis
fi
if [ $RUN_MEAN_ANALYSIS -eq 1 ]; then
    if [ $GENERATE_MAPS -eq 1 ]; then
        mean_analysis
    fi
fi
if [ $RUN_SKILL_ANALYSIS -eq 1 ]; then
    skill_analysis
fi
if [ $RUN_HEATMAP_ANALYSIS -eq 1 ]; then
    heatmap_analysis
fi
#############################################################################

# Record the end time and calculate elapsed time
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

print_header "* * *               MONAN Analysis finished.               * * *"

# Print total runtime in HH:MM:SS format
printf "Total runtime: %02d:%02d:%02d\n" \
       $((ELAPSED/3600)) \
       $((ELAPSED%3600/60)) \
       $((ELAPSED%60))

echo -e "\n############################################"
echo " ______  _____  _   _  _____  _____  _    _ "
echo "|  ____||_   _|| \ | ||_   _|/ ____|| |  | |"
echo "| |__     | |  |  \| |  | | | (___  | |__| |"
echo "|  __|    | |  | .   |  | |  \___ \ |  __  |"
echo "| |      _| |_ | |\  | _| |_ ____) || |  | |"
echo "|_|     |_____||_| \_||_____||_____/|_|  |_|"
echo -e "############################################\n"
