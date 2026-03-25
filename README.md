# 🍎 MacOS Widgets for Windows

> Widgets estilo macOS/iOS rodando nativamente no Windows — com efeito de cores dinâmicas da capa do álbum, clima em tempo real e barra de pesquisa Spotlight.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/PyQt6-6.x-green?style=flat-square"/>
  <img src="https://img.shields.io/badge/Windows-10%2F11-0078D4?style=flat-square&logo=windows&logoColor=white"/>
  <img src="https://img.shields.io/badge/license-MIT-orange?style=flat-square"/>
</p>

---

## ✨ Widgets incluídos

### 🎵 Music Widget
Widget de música que lê a mídia tocando no sistema (Spotify, YouTube, etc.) com efeito **iOS Color Flood** — ao passar o mouse, as cores dominantes da capa do álbum "invadem" o fundo do widget, exatamente como no iOS 16.

- Leitura automática via Windows Media Session API
- Efeito de gradiente animado extraído da capa em tempo real
- Controles de reprodução (anterior, play/pause, próximo)
- Modo mini (duplo clique) e modo completo
- Capa com bordas arredondadas estilo Apple

### 🌤️ Weather Widget
Widget de clima com visual glassmorphism azul.

- Temperatura, descrição e previsão
- Ícone customizável
- Totalmente configurável

### ⌕ Spotlight Search
Barra de pesquisa estilo macOS Spotlight, ativada com `Ctrl + Space`.

- Calculadora matemática segura (`sin`, `sqrt`, `pi`, etc.)
- Comandos rápidos (`yt`, `g`, `w`, `maps`, `def`, `gh`, `mail`)
- Histórico persistente de buscas
- Dropdown de resultados com navegação por teclado
- Efeito Acrylic blur (vidro fosco nativo do Windows)

### 📝 Notes Widget
Widget de notas estilo Apple Notes fixo no desktop.

- Fundo amarelo creme idêntico ao Notes real
- Animação suave de expand/collapse
- Salvamento automático
- Contagem de palavras em tempo real
- Fixo atrás de todas as janelas

---

## 🖼️ Preview

> *Widgets sobre wallpaper do Windows 11*

```
┌─────────────────────────────────────────┐
│  🎵  SICKO MODE              ✕          │
│  ████  Travis Scott                     │
│  ████  ──────────●───────────           │
│  ████     ◁◁    ▷    ▷▷                 │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  Minha Cidade              🌤           │
│  23°                                    │
│  Céu Limpo          Previsão: Ensol.    │
└─────────────────────────────────────────┘
```

---

## 📦 Instalação

### Pré-requisitos

- Python **3.10** ou superior
- Windows **10** ou **11**
- Git

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/macos-widgets-windows.git
cd macos-widgets-windows
```

### 2. Instale as dependências

```bash
pip install -r requirements.txt
```

### 3. Execute

```bash
# Todos os widgets juntos
python mac.pyw

# Spotlight separado
python spotlight.py

# Widget de notas separado
python notas_widget.py

# Cadastrar rosto no FaceID
python cadastrar_rosto.py
```

---

## 🗂️ Estrutura do projeto

```
macos-widgets-windows/
│
├── mac.pyw                  # Widget de música + clima
├── spotlight.py             # Barra de pesquisa Spotlight
├── notas_widget.py          # Widget de notas
│
├── faceid/
│   ├── autenticar.py        # Autenticação facial no login
│   ├── cadastrar_rosto.py   # Cadastro de rosto (1x)
│   └── instalar_startup.py  # Registra no startup do Windows
│
├── assets/
│   └── apple_clima.png      # Ícone do clima
│
├── requirements.txt
└── README.md
```

---

## 📋 requirements.txt

```
PyQt6>=6.4.0
keyboard>=0.13.5
winsdk>=1.0.0b10
colorthief>=0.2.1
Pillow>=10.0.0
simpleeval>=0.9.13
face_recognition>=1.3.0
opencv-python>=4.8.0
numpy>=1.24.0
```

---

## ⌨️ Atalhos

| Atalho | Ação |
|--------|------|
| `Ctrl + Space` | Abrir / fechar Spotlight |
| `↑` `↓` | Navegar nos resultados do Spotlight |
| `Enter` | Executar item selecionado |
| `Esc` | Fechar Spotlight / recolher nota |
| Duplo clique | Alternar modo mini ↔ completo (música) |
| Arrastar | Mover qualquer widget |

---

## ⌕ Comandos do Spotlight

| Digite | Resultado |
|--------|-----------|
| `2 + 2 * 3` | Calcula e copia para área de transferência |
| `sin(pi/2)` | Funções matemáticas avançadas |
| `yt lofi hip hop` | Busca no YouTube |
| `g python tutorial` | Busca no Google |
| `w inteligência artificial` | Wikipedia em português |
| `maps paris` | Google Maps |
| `def serendipidade` | Dicionário (dicio.com.br) |
| `gh pytorch` | GitHub Search |
| `mail assunto` | Novo e-mail no Gmail |
| qualquer coisa | Busca padrão no Google |

---

## 🔒 FaceID no Login (opcional)

Sistema de autenticação facial que roda automaticamente ao iniciar o Windows.

### Setup

```bash
# 1. Cadastre seu rosto (uma vez)
python faceid/cadastrar_rosto.py

# 2. Instale no startup (como Administrador)
python faceid/instalar_startup.py

# 3. Desinstalar
python faceid/instalar_startup.py --desinstalar
```

### Como funciona

1. Você entra no Windows → FaceID abre automaticamente
2. Câmera detecta seu rosto em 5 frames consecutivos → ✅ acesso liberado
3. Se não reconhecer em 20s → pede senha de fallback (3 tentativas)
4. Se senha também falhar → 🔒 Windows é bloqueado

> **Nota:** Requer [CMake](https://cmake.org/download/) instalado para o `face_recognition`.

---

## 🎨 Efeito iOS Color Flood

O Music Widget extrai as **3 cores dominantes** da capa do álbum usando `colorthief` e anima um gradiente diagonal sobre o fundo do widget quando você passa o mouse.

```
Hover  →  Gradiente aparece (500ms, OutCubic)
Leave  →  Gradiente some  (700ms, OutCubic)
```

As cores são extraídas em thread separada para não travar a UI, e são saturadas levemente para ficarem mais vivas (igual ao iOS).

---

## ⚙️ Configurações

### Music Widget (`mac.pyw`)
```python
# Acrylic tint (hex ARGB)
accent.GradientColor = 0x00121212

# Opacidade máxima do gradiente (0–255)
alpha = int(self._opacity * 210)
```

### Spotlight (`spotlight.py`)
```python
W             = 680    # Largura da janela
H_BAR         = 64     # Altura da barra de input
MAX_ROWS      = 8      # Máximo de resultados visíveis
MAX_HISTORY   = 30     # Itens no histórico
TOLERANCIA    = 0.50   # Sensibilidade do FaceID (menor = mais rigoroso)
```

### Notes Widget (`notas_widget.py`)
```python
W         = 300    # Largura
H_OPEN    = 340    # Altura expandida
ANIM_MS   = 380    # Duração da animação (ms)
```

---

## 🛠️ Tecnologias

| Lib | Uso |
|-----|-----|
| `PyQt6` | Interface gráfica, animações, rendering |
| `winsdk` | Windows Media Session API (música atual) |
| `colorthief` | Extração de paleta de cores da capa |
| `Pillow` | Processamento de imagem |
| `keyboard` | Hotkey global (`Ctrl+Space`) |
| `simpleeval` | Calculadora segura no Spotlight |
| `face_recognition` | Reconhecimento facial (FaceID) |
| `ctypes` | Acrylic blur, HWND, SetWindowPos |

---

## 🤝 Contribuindo

Pull requests são bem-vindos! Para mudanças maiores, abra uma issue primeiro para discutir o que você gostaria de mudar.

1. Fork o projeto
2. Crie sua branch (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'Add nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

---

## 📄 Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.

---

## 🙏 Créditos

Inspirado pela linguagem visual do **macOS** e **iOS** da Apple.
Desenvolvido com ❤️ em Python + PyQt6.
