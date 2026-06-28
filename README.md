# Sistema de Laudo Venoso — Eco-Doppler de Membro Inferior

App em Streamlit para preencher o laudo de eco-doppler venoso durante o
exame, com geração automática de texto e de um desenho esquemático
(venograma) da perna.

## Arquivos deste repositório

```
app.py            ← TODO o app está aqui, em um único arquivo
requirements.txt  ← lista de bibliotecas que o Railway instala automaticamente
railway.json      ← diz ao Railway como rodar o app
Procfile          ← mesma coisa que o railway.json, formato alternativo
README.md         ← este arquivo
```

Por que tudo em um arquivo só? Porque você edita direto pela interface
web do GitHub (sem terminal, sem git local) — manter um único `app.py`
é muito mais simples de atualizar por lá do que ficar navegando entre
várias pastas e arquivos.

## Como editar

1. No GitHub, abra `app.py`.
2. Clique no ícone de lápis (✏️) no canto superior direito do arquivo.
3. Encontre a parte que você quer mudar — o arquivo tem comentários tipo:
   ```
   # =====================================================================
   # 6. SEÇÕES DA INTERFACE
   # =====================================================================
   ```
   Esses comentários dividem o arquivo em blocos, então dá pra usar
   Ctrl+F (ou Cmd+F) pra achar rápido o bloco que você quer.
4. Edite, role até o final da página e clique em **"Commit changes"**.

## O que acontece depois de salvar (commit)

Se o app já está conectado ao Railway, ele detecta o commit automaticamente
e refaz o deploy sozinho — geralmente fica pronto em 1 a 3 minutos. Você
pode acompanhar o progresso no painel do Railway, na aba **Deployments**.

## Como conectar este repositório ao Railway (primeira vez)

1. Entre em [railway.app](https://railway.app) e faça login com sua conta GitHub.
2. **New Project** → **Deploy from GitHub repo** → selecione este repositório.
3. O Railway vai detectar o `railway.json` e configurar tudo automaticamente.
4. Vá em **Settings → Networking** e clique em **Generate Domain** para
   conseguir o link público do app (algo como `seu-app.up.railway.app`).

## O que esse app faz

- **Seções 1–4**: você (ou a assistente) preenche os achados do exame —
  lateralidade, sistema profundo, sistema superficial (safenas), medidas
  e perfurantes. Cada campo técnico tem um ícone de ajuda (?) ou uma
  caixinha azul de dica explicando o termo em linguagem simples.
- **Seção 5 — Laudo Final**: o texto do laudo é montado automaticamente
  a partir do que foi preenchido, mas pode ser editado livremente antes
  de copiar.
- **Seção 6 — Venograma**: um desenho esquemático da perna é gerado
  **automaticamente** a partir dos mesmos dados:
  - **Azul** = trajeto normal
  - **Vermelho** = refluxo (incompetência valvular)
  - **Preto** = trombose
  - **Ponto âmbar** = perfurante insuficiente
  
  Esse desenho é só uma referência esquemática (não é uma imagem
  anatômica de precisão) — serve para visualizar rapidamente onde estão
  os achados enquanto o exame está sendo feito. Por cima dele, ainda é
  possível desenhar manualmente (lápis, linha, círculo) caso queira
  marcar algo que o desenho automático não capturou.

## Avisos de consistência

O app avisa (mas não te impede de continuar) quando:
- O sistema profundo foi marcado como "alterado" mas nenhuma veia foi escolhida.
- Foram marcados dois achados que não fazem sentido juntos na mesma veia
  (ex.: "veia removida em cirurgia" e "veia com refluxo" ao mesmo tempo).

## Limitações conhecidas

- O venograma automático é esquemático/aproximado — a posição exata de
  cada perfurante na imagem é uma estimativa visual, não uma medida
  geométrica precisa.
- Os campos de distância (cm) aceitam qualquer texto digitado — não há
  validação de que o valor é realmente um número.
- Os dados preenchidos não são salvos entre sessões — ao recarregar a
  página ou fechar a aba, é necessário preencher novamente (ou copiar o
  laudo antes de saIr).
