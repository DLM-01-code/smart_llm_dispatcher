# Сначала необходимо поставить streamlit на пайтон
(В терминале powershell)
```
pip install streamlit
```


# Команды для скачивания моделей в powershell



# Скачать Ollama
```
irm https://ollama.com/install.ps1 | iex
```
# Скачать модели:

```
ollama pull mistral:7b
ollama pull codellama:34b
ollama pull gemma3:27b
ollama pull llama3.3:70b
ollama pull deepseek-r1:32b
ollama pull qwen2.5-coder:32b
ollama pull gemma4:latest
ollama pull qwen2.5vl:7b
ollama pull gemma2:latest
ollama pull deepseek-r1:7b
ollama pull qwen2.5-coder:7b
ollama pull llama3.1:latest
ollama pull phi4:latest
ollama pull qwen3:8b
```

# Или одной командой все сразу

```
ollama pull mistral:7b; `
ollama pull codellama:34b; `
ollama pull gemma3:27b; `
ollama pull llama3.3:70b; `
ollama pull deepseek-r1:32b; `
ollama pull qwen2.5-coder:32b; `
ollama pull gemma4:latest; `
ollama pull qwen2.5vl:7b; `
ollama pull gemma2:latest; `
ollama pull deepseek-r1:7b; `
ollama pull qwen2.5-coder:7b; `
ollama pull llama3.1:latest; `
ollama pull phi4:latest; `
ollama pull qwen3:8b
```
--- 

# Открыть командой streamlit:

```
streamlit run universal_chat_py
```

# First you need to put StreamLite on Python
(In the powershell terminal)
```
pip install streamlit
```


# Commands for downloading models in powershell



# Download Ollama
```
irm https://ollama.com/install.ps1 | iex
```
# Download all models:

```
ollama pull mistral:7b
ollama pull codellama:34b
ollama pull gemma3:27b
ollama pull llama3.3:70b
ollama pull deepseek-r1:32b
ollama pull qwen2.5-coder:32b
ollama pull gemma4:latest
ollama pull qwen2.5vl:7b
ollama pull gemma2:latest
ollama pull deepseek-r1:7b
ollama pull qwen2.5-coder:7b
ollama pull llama3.1:latest
ollama pull phi4:latest
ollama pull qwen3:8b
```

# Or one command for full models

```
ollama pull mistral:7b; `
ollama pull codellama:34b; `
ollama pull gemma3:27b; `
ollama pull llama3.3:70b; `
ollama pull deepseek-r1:32b; `
ollama pull qwen2.5-coder:32b; `
ollama pull gemma4:latest; `
ollama pull qwen2.5vl:7b; `
ollama pull gemma2:latest; `
ollama pull deepseek-r1:7b; `
ollama pull qwen2.5-coder:7b; `
ollama pull llama3.1:latest; `
ollama pull phi4:latest; `
ollama pull qwen3:8b
```

# Open with streamlit:

```
streamlit run universal_chat_py
```