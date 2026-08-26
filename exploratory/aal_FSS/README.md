# Fractions Skill Score (FSS)

O **Fractions Skill Score (FSS)** reduz a dependência de uma coincidência exata ponto a ponto, comparando as frações de ocorrência do evento em diferentes escalas espaciais (**Roberts e Lean, 2008**).

---

## 1. Conversão da precipitação em evento binário

A precipitação é convertida em um evento binário para cada limiar considerado:

**1, 2, 5, 10, 20 e 50 mm**

Para a previsão:

$$
I_F(x)=
\begin{cases}
1, & P_F(x)\geq \mathrm{Limiar} \\
0, & P_F(x)<\mathrm{Limiar}
\end{cases}
$$

Para a observação:

$$
I_O(x)=
\begin{cases}
1, & P_O(x)\geq \mathrm{Limiar} \\
0, & P_O(x)<\mathrm{Limiar}
\end{cases}
$$

Os índices **F** e **O** representam, respectivamente, **previsão** e **observação**.

---

## 2. Fração de ocorrência do evento na vizinhança

Para cada ponto da grade, calcula-se a fração de pixels em que o evento ocorre dentro de uma janela espacial de tamanho $n \times n$.

Para a previsão:

$$f_F^{(n)}(x)=\frac{1}{N_n}\sum I_F(y)$$

Para a observação:

$$f_O^{(n)}(x)=\frac{1}{N_n}\sum I_O(y)$$

onde $N_n$ representa o número de pontos válidos dentro da vizinhança.

### Exemplo conceitual

Considere o campo binário:

|   |   |   |   |   |
|---:|---:|---:|---:|---:|
| **1** | 0 | 0 | **1** | 0 |
| 0 | **1** | **1** | 0 | 0 |
| 0 | **1** | **1** | **1** | 0 |
| 0 | 0 | **1** | 0 | **1** |
| **1** | 0 | 0 | **1** | 0 |

Para uma **janela 3 × 3** contendo 6 ocorrências:

$$f^{(3)}(x)=\frac{6}{9}=0.67$$

Para uma **janela 5 × 5** contendo 11 ocorrências:

$$f^{(5)}(x)=\frac{11}{25}=0.44$$

Assim, o FSS avalia o desempenho da previsão em diferentes escalas espaciais, reduzindo a exigência de coincidência exata ponto a ponto.

---

## 3. Fractions Brier Score (FBS)

O **Fractions Brier Score (FBS)** mede o erro quadrático médio entre as frações previstas e observadas em todos os pontos válidos do domínio.

$$FBS_n=\frac{1}{N_D}\sum_{x\in D}\left[f_F^{(n)}(x)-f_O^{(n)}(x)\right]^2$$

onde:

- $D$ representa o domínio de avaliação;
- $N_D$ representa o número de pontos válidos do domínio;
- $n$ representa o tamanho da janela espacial.

---

## 4. Erro de referência — $FBS_{\mathrm{worst},n}$

O erro de referência é definido por:

$$FBS_{\mathrm{worst},n}=\frac{1}{N_D}\sum_{x\in D}\left[\left(f_F^{(n)}(x)\right)^2+\left(f_O^{(n)}(x)\right)^2\right]$$

O $FBS_{\mathrm{worst},n}$ representa o valor do erro de referência quando as frações previstas e observadas apresentam a menor correspondência espacial possível, ou seja, quando não há sobreposição entre elas.

---

## 5. Fractions Skill Score

O FSS é obtido pela normalização do FBS pelo erro de referência:

$$\boxed{FSS_n=1-\frac{FBS_n}{FBS_{\mathrm{worst},n}}}$$

O valor do FSS varia, em geral, entre **0 e 1**:

- **FSS = 1**: correspondência perfeita entre as frações previstas e observadas;
- **FSS próximo de 0**: baixa correspondência espacial entre previsão e observação;
- o valor do FSS deve ser interpretado em função do **limiar de precipitação**, da **escala espacial da janela**, do **lead time**, do **domínio** e da **referência observacional**.

---

## Referência

Roberts, N. M., e Lean, H. W. (2008).
