# Contorno CAD — primeira versão executável

[Português brasileiro](README_PT.md) | [English](README.md)

**Idioma da interface:** escolha Português (PT) ou English (EN) em **Language / Idioma**, no topo do aplicativo. A troca preserva os dados e a geometria do projeto. As traduções são locais, sem API.

Aplicativo novo em Python/Streamlit, criado nesta pasta sem reutilizar código ou arquitetura do Formlab. Funciona localmente e não chama APIs de IA, serviços de reconstrução ou serviços pagos. A entrada chama-se **iniciar_cad.py**; nenhum `app.py` anterior foi modificado.

## Obter o projeto

```bash
git clone https://github.com/felipe-maia-vassalo/contorno-cad.git
cd contorno-cad
```

Também é possível usar **Code → Download ZIP** no GitHub e entrar na pasta extraída. O inglês é o idioma inicial da interface; português continua disponível em **Language / Idioma**.

## Instalar após extrair o ZIP / em outro Mac

Validado em macOS 27.0.1, Apple Silicon, Python 3.12.14. Os pacotes NumPy/SciPy arm64 fixados pedem macOS 14 ou posterior. Instale **Python 3.12** pelo [site oficial](https://www.python.org/downloads/), sem substituir o Python de outros aplicativos. O Python 3.13 existente neste Mac não foi usado para este projeto. Não use `sudo pip`.

Entre na pasta `contorno_cad` extraída e execute:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/preparar_casadi.py
python scripts/preparar_casadi.py --verificar
streamlit run iniciar_cad.py
```

**A preparação CasADi é obrigatória:** remove solvers opcionais que incluem um binário METIS com licença restritiva, conserva o núcleo LGPL utilizado pelo CadQuery e arquiva os avisos legais. O aplicativo verifica a composição antes de importar CadQuery. Se reinstalar pacotes, execute o preparador novamente. Veja `docs/LICENCAS.md`. Não distribua a wheel/ambiente original sem essa revisão. Não há custo de licença para usar a seleção preparada, respeitadas suas obrigações.

Para abrir novamente em outro dia:

```bash
cd "/caminho/para/contorno_cad"
source .venv/bin/activate
streamlit run iniciar_cad.py
```

## Primeiro modelo, com a ponteira incluída

1. Abra o **Painel inicial** e clique em **Abrir exemplo calibrado da ponteira**.
2. Visite **Imagem para CAD**: confira foto, recorte e contornos. A foto preta original foi realmente processada; o exemplo já carrega a calibração e o perfil resultantes.
3. Em **Editor de perfil 2D**, ajuste X/raio e Y/altura na tabela e clique em **Aplicar coordenadas do perfil**. Linhas podem ser adicionadas e removidas.
4. Em **Editor CAD**, mantenha **Ponteira • revolução com topo spline** e clique em **Gerar / atualizar modelo**. O visualizador abre na mesma página.
5. Altere **Elevação do topo** de 6 para 9 mm e gere novamente: a altura total passa de 45 para 48 mm. **Formato da spline superior** modifica a curva sem impor raio circular constante. Controles personalizados também estão disponíveis.
6. Defina diâmetro interno e profundidade do encaixe; confira a seção transversal. O encaixe abre na base deste modelo. Os 22,22 mm indicam o tubo nominal e não garantem ajuste de fabricação sem folga medida.
7. Em **Exportar projeto**, clique em **Validar geometria e preparar arquivos**. Baixe STL, STEP, HTML, JSON ou o ZIP do projeto.
8. Salve o JSON antes de fechar. Em outra sessão, use **Reabrir projeto JSON → Reabrir projeto salvo** e gere o modelo novamente.

O exemplo preto usa a silhueta lateral direita, 45 mm **aproximados** para escala, altura lateral 39 mm e topo 6 mm **hipotético**. A lateral é remapeada para 39 mm; seus raios vêm da fotografia calibrada e continuam aproximados. A fotografia branca também foi processada, e a marcação verde forneceu controles de uma spline no exemplo `examples/branca`. Seus 45 mm são uma hipótese de teste independente: não foram medidos na peça branca.

## Da sua fotografia ao CAD

A página **Imagem para CAD** contém uma descrição completa da fotografia adequada. Prefira objeto inteiro, foco nítido, fundo contrastante, câmera perpendicular ao perfil e dimensão conhecida no mesmo plano. Transparência, reflexos, sombras e perspectiva prejudicam a extração. Uma foto não recupera superfícies ocultas.

1. Envie `.jpg`, `.jpeg` ou `.png` (até 30 MB/24 MP). Confira o nome e a resolução confirmados no app.
2. Ajuste recorte, contraste e filtro. Use **Escuro** para peça escura/fundo claro, **Claro** para o contrário, **Fundo colorido** para objeto pouco saturado ou **Canny** para bordas.
3. Escolha o contorno; use **contorno fechado** para extrusão ou **lateral direita** para revolução/ponteira. A lateral automática presume simetria em torno do centro do contorno. Corrija o eixo quando necessário.
4. No editor sobre a foto, escolha **Marcar os dois pontos de calibração**, clique em dois pontos cuja distância você mediu e clique em **Aplicar pontos à etapa**. Também pode marcar os extremos do contorno e conferir suas coordenadas numericamente.
5. Informe a distância em mm, eixo/origem X e base/origem Y. Clique em **Confirmar calibração e converter perfil para mm**. Sem confirmação, não há escala física confiável.
6. Corrija o perfil: selecione e arraste pontos; adicione/remova com as ferramentas do quadro; confirme em **Aplicar pontos à etapa**. A tabela permite coordenadas, arcos e splines. Arcos precisam de ponto intermediário. Grupos spline podem receber direções de tangência.
7. Escolha revolução, extrusão com profundidade ou reconstrução assistida com caixas/cilindros/tubos/loft. Gere, inspecione, altere e regenere.

A curva calculada pelo CAD aparece no gráfico de perfil sobre a foto. O quadro de arraste mostra segmentos entre os pontos de controle. O topo acrescentado da ponteira é conferido no sólido/visualizador; a posição física não é deduzida automaticamente da foto.

## Edição, importação e exportação

- Fillet e chanfro com seleção por posição/orientação de arestas; furos com posição/diâmetro/profundidade; cavidades, união e subtração com caixas; escala; medidas e perfil editáveis. A lista de operações admite edição numérica JSON. Falhas deixam o modelo anterior desatualizado e bloqueiam sua exportação como resultado atual.
- Reconstrução assistida combina caixas, cilindros, tubos e loft entre círculos. O motor também aceita loft com seções retangulares em JSON.
- STEP válido permanece B-Rep sólido. STL/OBJ/GLB/GLTF são malhas: mover, girar, escalar, selecionar componentes e exportar são possíveis; não existe histórico CAD recuperado. DAE exige dependência opcional não incluída/testada. SKP nativo não é aceito.
- A visualização/exportação de importados é do **componente ativo**. O arquivo fonte com os demais componentes permanece no JSON; o app não é um editor completo de montagens.
- STL só é liberado se fechado, com orientação consistente e volume positivo. Na tesselação CAD, faces degeneradas/duplicadas podem ser removidas sem modificar posições, volume ou limites; isso fica registrado. Buracos não são preenchidos automaticamente.
- STEP é reimportado e comparado em validade, número de sólidos, volume e limites. Validade geométrica não certifica tolerâncias, material, resistência, contração de injeção ou ajuste do produto.
- HTML contém o visualizador Plotly para funcionar sem CDN. JSON preserva fonte, calibração, perfil, parâmetros e operações; ZIP agrupa as exportações.

## Testes e arquivos de demonstração

Execute na pasta do projeto, com o ambiente ativado:

```bash
python -m pytest -q
python scripts/demonstrar.py
```

A demonstração lê os **dois JPEGs reais** incluídos, executa OpenCV, calibração, extração, construção, alteração, exportação, reimportação e persistência. Também cria e importa GLB/OBJ como formatos intermediários. Esses arquivos foram produzidos pela demonstração; não foram exportados de uma sessão real do SketchUp.

- `examples/modelo.stl` / `modelo.step` / `previa.html`: ponteira base.
- `examples/modificado/`: ponteira após alterar o topo.
- `examples/branca/`: fotografia branca, controles da marcação verde e modelo correspondente.
- `examples/perfil_extraido.json`, máscaras e sobreposições: evidências calculadas.
- `examples/demo_project.json`: exemplo reabrível com foto incorporada.
- `examples/importacao/`: formatos intermediários, transformações e exportações.
- `examples/relatorio_demonstracao.json`: medidas, volumes e verificações executadas.
- `docs/evidencias/`: capturas reais de navegador disponíveis; não confundir com sobreposições geradas pelo OpenCV.

Os relatórios de testes distinguem teste automatizado, navegação real e limitações de autorização do navegador. Não foi concluída uma validação visual manual de todas as ferramentas.

## Estrutura e documentação

`iniciar_cad.py` inicia a interface. `contorno_cad/ui.py` reúne as páginas, enquanto `imaging.py`, `profiles.py`, `cad.py`, `io3d.py`, `viewer.py` e `project.py` separam processamento, perfil, CAD, importação/exportação, visualizador e persistência. `tests/` contém testes unitários, integração e Streamlit. `scripts/` contém preparação e demonstração reproduzível.

Leia o inventário completo em `docs/FUNCIONALIDADES_E_LIMITACOES.md`, `docs/TESTES_AUTOMATIZADOS.md`, `docs/TESTES_INTERFACE.md`, `docs/LICENCAS.md`, `THIRD_PARTY_NOTICES.md` e `docs/IMPLANTACAO.md`. O relatório final está em `RELATORIO_DA_ENTREGA.md`.

## Erros frequentes

- **Preparação obrigatória ausente / componente opcional detectado:** ative a `.venv`, execute `python scripts/preparar_casadi.py` e reinicie.
- **No matching distribution:** confirme Python 3.12, macOS compatível e arquitetura nativa; não misture arm64 e Rosetta.
- **Nenhum contorno:** ajuste recorte/método/limiar ou desenhe o perfil.
- **Raio negativo:** mova o eixo para o centro correto e mantenha só uma lateral no modo revolução.
- **Encaixe atravessa a peça:** reduza diâmetro/profundidade ou aumente dimensões externas conscientemente.
- **Falha de fillet/chanfro:** reduza a medida, escolha outro grupo de arestas ou desfaça a operação.
- **Malha aberta:** use como referência; corrija no programa de origem. A exportação STL de fabricação permanece bloqueada.
- **Modelo desatualizado:** clique em Gerar / atualizar modelo após qualquer alteração.
- **Porta em uso:** rode `streamlit run iniciar_cad.py --server.port 8502` e abra a nova porta.

O servidor se limita a `127.0.0.1`. Para implantação interna com autenticação, HTTPS e limites de recursos, siga `docs/IMPLANTACAO.md`. A adaptação Windows ainda precisa de validação real.
