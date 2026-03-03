#!/bin/bash

# Para execucao em loop
# for dia in $(seq 1 15); do dia_formatado=$(printf "%02d" $dia); echo "Executando para 2025-12-$dia_formatado"; ./Gera_MONAN_precip_netcdf.sh 2025 12 "$dia_formatado" 00; done

DIRIN=/lustre/projetos/monan_adm/monan/ecf_PREOPER/MONAN-WorkFlow-OPER/MONAN_PRE_OPER/MONAN/scripts_CD-CT/dataout/flushout
#####################################################
if [ -z "$1" ] ;then
    echo "No argument supplied"
    echo enter YEAR in the form:  YYYY
    exit
fi
if [ -z "$2" ] ;then
    echo "No argument supplied"
    echo enter MONTH in the form:  MM
    exit
fi
if [ -z "$3" ] ;then
    echo "No argument supplied"
    echo enter DAY in the form:  DD
    exit
fi
if [ -z "$4" ] ;then
    echo "No argument supplied"
    echo enter TIME in the form:  00 or 12
    exit
fi
Y=${1} ; M=${2} ; D=${3} ; T={4}
#####################################################

date=${1}${2}${3}${4}
DIROU=/pesq/share/monan/monan_gam/netcdf/${1}${2}
mkdir ${DIROU}/${date}

#--------------------- select rainc,rainnc
files=${DIRIN}/${date}
#/bin/ls ${files}
cd ${files}
fcst_files=`/bin/ls -1tr  MONAN*nc`
echo ${fcst_files}
#-----
for f in ${fcst_files}
do
cdo selname,rainc,rainnc ${f} ${DIROU}/${date}/prec_${f}
echo ' --- '
done

#--------------------- concatenate all files
cd ${DIROU}/${date}

filename1=MONAN_DIAG_G_POS_GFS
filename2=x5898242L55.nc
fcst_files=`/bin/ls -1tr  prec_MONAN*nc`
catfile=${filename1}_${date}_prec_${filename2}
cdo -z zip9 cat $fcst_files x${catfile}

#--------------------- fix the initial time and time interval
cdo -z zip9 -r settaxis,${Y}-${M}-${D},${T}:00:00,3h x${catfile} ${catfile}

#--------------------- delete tmp files
/bin/rm  $fcst_files x${catfile}
