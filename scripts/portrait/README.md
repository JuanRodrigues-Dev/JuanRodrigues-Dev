# Banner do perfil (retrato em pontilhado + system.info)

O arquivo `assets/banner.svg` já vem pronto — gerado a partir da sua foto.
Você só precisa mexer aqui se quiser trocar a foto ou editar os campos da
tabela de informações.

## Editar os campos de texto (SYSTEM.INFO)

Abra `build_banner.py` e edite a lista `FIELDS` no topo do arquivo — cada
item é um par (rótulo, valor). Depois rode o script de novo (veja abaixo).

## Trocar a foto e regenerar

1. Coloque a nova foto em `assets/source-photo.png` (na raiz do repositório,
   dentro da pasta `assets/`). Fotos com boa iluminação e um enquadramento de
   busto (cabeça + ombros, olhando pra frente) funcionam melhor.
2. Instale as dependências (uma vez só):
   ```bash
   pip install -r scripts/portrait/requirements.txt
   ```
3. Rode o gerador a partir da raiz do repositório:
   ```bash
   python3 scripts/portrait/build_banner.py
   ```
4. Confira `assets/banner.svg` gerado. Se a silhuete sair com pedaços do
   fundo grudados (móveis, parede etc.), ajuste as coordenadas em
   `segment_person()` dentro de `build_portrait.py` — os comentários no
   código explicam cada retângulo/semente usada pelo GrabCut.

Esse processo é manual (não roda pelo GitHub Actions), porque é uma foto
sua — só faz sentido regenerar quando você trocar a imagem ou os campos de
texto. Já as métricas em `assets/stats-card.svg`, `radar-langs.svg` e
`radar-skills.svg` continuam sendo atualizadas automaticamente todo dia
pelo workflow em `.github/workflows/update-metrics.yml`.

## Se a imagem não atualizar depois de um novo commit

O GitHub serve imagens do README através de um proxy (`camo`) que faz
cache **por URL exata**. Como o caminho `assets/banner.svg` não muda a cada
commit, é possível que ele continue mostrando a versão antiga por um
tempo, mesmo depois do seu push ter dado certo.

Solução: no `README.md`, a URL do banner termina com `?v=3`. Toda vez que
você atualizar `assets/banner.svg` (nova foto, nova animação, etc.),
aumente esse número (`?v=4`, `?v=5`, ...). Isso muda a URL aos olhos do
proxy e força ele a buscar o arquivo de novo.
