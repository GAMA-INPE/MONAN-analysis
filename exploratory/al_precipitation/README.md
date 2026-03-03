# Scripts_Lyra_INPE

## Linguagens
 - Python
 - Shell script
 - CDO
 
## Autor
André Lyra

Scripts para processamento, plotagem, verificação e avaliação de precipitação de 24 horas do modelo MONAN,
incluindo comparações com GPM IMERG, GSMAP e MSWEP.

O fluxo inclui geração de acumulados, cálculo de métricas contínuas e categóricas, geração figuras e salvamento de produtos em formato png(300dpi), NetCDF e txt.

## Visão Geral do Fluxo de Execução:

1. Geração dos acumulados de precipitação de 24h do MONAN  
	MONAN_nc_24h_acum_newcolorbar.py

2. Cálculo e plotagem do Bias MONAN vs observações (GPM-IMERG, GSMaP e MSWEP)  
	Bias_MONAN_x_GPM_x_GSMAP_x_MSWEP.py

3. Cálculo e plotagem do MAE e RMSE MONAN vs observações 
	RMSE_MONAN_x_GPM_x_GSMAP_x_MSWEP.py

4. Cálculo da tabela de contigência e de Skill Scores para limiares de precipitação  
	Skill_score_MONAN_x_GPM_x_GSMAP_x_MSWEP.py

5. Processamento mensal por meio de scripts Shell e CDO 
	Gera_monthly_mean_Bias.sh
	Gera_monthly_mean_MAE_RMSE.sh
	Gera_monthly_sum_Skill.sh

6. Plotagem dos índices mensais   
	Mean_Bias_MONAN_BAM_GFS.py 
	Mean_MAE_MONAN_BAM_GFS.py
	Mean_RMSE_MONAN_BAM_GFS.py
    Mean_Skill_score_MONAN_BAM_GFS.py


