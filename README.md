# Terceira Ponte

[![HACS][badge-hacs]][link-hacs]
[![GitHub Release][badge-release]][link-release]
[![Home Assistant][badge-ha]][link-ha]
[![GitHub Commit Activity][badge-commit-activity]][link-commits]
[![HACS Validation][badge-hacs-validation]][link-hacs-validation]
[![Hassfest][badge-hassfest]][link-hassfest]
[![Tests][badge-tests]][link-tests]
[![License][badge-license]][link-license]

As quatro câmeras públicas da **Terceira Ponte** (Vitória–Vila Velha, ES) como entidades `camera` no Home Assistant, direto do serviço da CETURB-ES.

![Terceira Ponte](docs/images/dashboard-preview.png)

## Recursos

- 4 câmeras com os mesmos nomes do site da CETURB, por sentido do tráfego
- Cache curto e configurável: abrir o dashboard em vários aparelhos não multiplica as requisições
- Token JWT público renovado automaticamente; falhas passageiras são repetidas

## Requisitos

- Home Assistant 2026.10 ou mais recente
- Acesso à internet (o serviço `terceiraponte.ceturb.es.gov.br` é público e não pede conta)

## Instalação

### HACS (recomendado)

[![Abrir este repositório no HACS da sua instância do Home Assistant.][badge-my-hacs]][link-my-hacs]

1. Clique no botão acima, ou abra **HACS → ⋮ → Repositórios personalizados** e adicione
   `https://github.com/chiconws/ha-terceira-ponte` com o tipo **Integração**.
2. Procure por **Terceira Ponte** no HACS e clique em **Baixar**.
3. Reinicie o Home Assistant.

### Manual

1. Baixe a [versão mais recente][link-release].
2. Copie `custom_components/terceira_ponte` para a pasta `custom_components` da sua
   configuração do Home Assistant.
3. Reinicie o Home Assistant.

## Configuração

[![Configurar Terceira Ponte na sua instância do Home Assistant.][badge-my-config]][link-my-config]

1. Vá em **Configurações → Dispositivos e serviços → Adicionar integração**.
2. Procure por **Terceira Ponte** e siga os passos.

| Campo | Descrição |
| --- | --- |
| (nenhum) | Basta confirmar; não há login |

Em **Configurar**, **Atualizar imagem a cada** (5 a 60 s, padrão 10 s) define por quanto tempo a mesma imagem é reaproveitada.

## Entidades

| Entidade | Plataforma | Descrição |
| --- | --- | --- |
| Subida Sentido Vila Velha | `camera` | Snapshot JPEG |
| Descida Sentido Vila Velha | `camera` | Snapshot JPEG |
| Subida Sentido Vitória | `camera` | Snapshot JPEG |
| Descida Sentido Vitória | `camera` | Snapshot JPEG |

## Solução de problemas

- **Diagnóstico:** Configurações → Dispositivos e serviços → Terceira Ponte → ⋮ →
  **Baixar diagnóstico** (credenciais são ocultadas). Anexe o arquivo ao abrir um bug.
- **Logs de depuração:**

```yaml
logger:
  logs:
    custom_components.terceira_ponte: debug
```

## Exemplo: resumo do trânsito com IA

O feed não traz dados de trânsito, mas o Home Assistant pode analisar a imagem
com qualquer integração de IA que ofereça uma entidade AI Task (OpenAI, Google
Gemini, Ollama etc.). Esta automação manda, em dias úteis às 7h, uma
notificação com a foto e um resumo do trânsito:

```yaml
alias: Trânsito na Terceira Ponte
triggers:
  - trigger: time
    at: "07:00:00"
conditions:
  - condition: time
    weekday: [mon, tue, wed, thu, fri]
actions:
  - action: ai_task.generate_data
    data:
      task_name: Trânsito Terceira Ponte
      instructions: >-
        Esta é uma câmera da Terceira Ponte, em Vitória/ES. Diga em uma frase
        curta se o trânsito está livre, moderado ou congestionado.
      attachments:
        - media_content_id: media-source://camera/camera.ceturb_terceira_ponte_subida_sentido_vila_velha
          media_content_type: image/jpeg
    response_variable: transito
  - action: notify.mobile_app_seu_celular
    data:
      title: Terceira Ponte
      message: "{{ transito.data }}"
      data:
        image: /api/camera_proxy/camera.ceturb_terceira_ponte_subida_sentido_vila_velha
```

Ajuste o `entity_id` da câmera e o serviço `notify` para os da sua instalação.

## Limitações conhecidas

- O feed é snapshot JPEG, não vídeo.
- Depende do serviço público da CETURB-ES, sem contrato documentado de atualização.

## Desenvolvimento

Veja o [AGENTS.md](AGENTS.md) para a estrutura do código. Verificações rápidas:

```bash
uv venv --python 3.14 .venv && uv pip install -r requirements_test.txt
python -m ruff check custom_components/terceira_ponte tests
python -m pytest
```

## Créditos

Imagens públicas da CETURB-ES: <https://terceiraponte.ceturb.es.gov.br/>.

## Licença

MIT, veja [LICENSE](LICENSE).

[badge-hacs]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
[badge-release]: https://img.shields.io/github/v/release/chiconws/ha-terceira-ponte
[badge-ha]: https://img.shields.io/badge/Home%20Assistant-2026.10%2B-41BDF5?logo=home-assistant
[badge-commit-activity]: https://img.shields.io/github/commit-activity/m/chiconws/ha-terceira-ponte
[badge-hacs-validation]: https://github.com/chiconws/ha-terceira-ponte/actions/workflows/hacs.yaml/badge.svg
[badge-hassfest]: https://github.com/chiconws/ha-terceira-ponte/actions/workflows/hassfest.yaml/badge.svg
[badge-tests]: https://github.com/chiconws/ha-terceira-ponte/actions/workflows/tests.yaml/badge.svg
[badge-license]: https://img.shields.io/github/license/chiconws/ha-terceira-ponte
[badge-my-hacs]: https://my.home-assistant.io/badges/hacs_repository.svg
[badge-my-config]: https://my.home-assistant.io/badges/config_flow_start.svg

[link-hacs]: https://hacs.xyz/
[link-release]: https://github.com/chiconws/ha-terceira-ponte/releases/latest
[link-ha]: https://www.home-assistant.io/
[link-commits]: https://github.com/chiconws/ha-terceira-ponte/commits/main
[link-hacs-validation]: https://github.com/chiconws/ha-terceira-ponte/actions/workflows/hacs.yaml
[link-hassfest]: https://github.com/chiconws/ha-terceira-ponte/actions/workflows/hassfest.yaml
[link-tests]: https://github.com/chiconws/ha-terceira-ponte/actions/workflows/tests.yaml
[link-license]: LICENSE
[link-my-hacs]: https://my.home-assistant.io/redirect/hacs_repository/?owner=chiconws&repository=ha-terceira-ponte&category=integration
[link-my-config]: https://my.home-assistant.io/redirect/config_flow_start/?domain=terceira_ponte
