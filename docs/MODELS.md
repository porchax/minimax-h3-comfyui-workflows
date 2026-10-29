# Модели и дополнительные компоненты

Модель — большой файл с обученными весами. JSON-схема хранит только его имя и настройки загрузки. **Ни GitHub, ни архив схем не заменяют скачивание весов.**

Пути ниже указаны относительно папки ComfyUI.

## Основной комплект H3

Эти пять файлов скачивает установщик. Для них сохранены точные ревизии и контрольные суммы в [models.json](../config/models.json). Общий размер — около 62 ГБ.

| Файл | Папка | Для чего нужен |
|---|---|---|
| `10Eros_Max_h3_TURBO-hybrid_beta5.safetensors` | `models/diffusion_models/` | Основная модель генерации |
| `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | `models/text_encoders/` | Понимание текста и референсов; тип CLIP = `minimax` |
| `minimax_h3_video_vae_fp16.safetensors` | `models/vae/` | Кодирование изображения и декодирование кадров |
| `minimax_h3_audio_vae_fp32.safetensors` | `models/vae/` | Работа со звуком H3 |
| `taeh3.safetensors` | `models/vae_approx/` | Быстрое приблизительное превью |

Источники: [TenStrip/10Eros-Max](https://huggingface.co/TenStrip/10Eros-Max), [Comfy-Org/MiniMax-H3](https://huggingface.co/Comfy-Org/MiniMax-H3), [Kijai/MiniMax-H3-TAE](https://huggingface.co/Kijai/MiniMax-H3-TAE).

## Маски: SAM3 или Sapiens2

Нужны только при использовании соответствующей обработки видеореференса.

| Файл из исходной схемы | Папка | Источник |
|---|---|---|
| `sam3.1_multiplex_fp16.safetensors` | `models/checkpoints/` | [Comfy-Org/sam3.1](https://huggingface.co/Comfy-Org/sam3.1) |
| `sapiens2_1b_seg.safetensors` | `models/sapiens2/seg/` | [facebook/sapiens2-seg-1b](https://huggingface.co/facebook/sapiens2-seg-1b), инструкция путей в [нодах Sapiens2](https://github.com/kijai/ComfyUI-Sapiens2) |

Эти веса не входят в основной автоматический набор. Доступ, фактическое имя файла и условия скачивания проверяйте по карточке модели. После установки повторно выберите файл в загрузчике.

## Фотокарусель: FLUX и её референсы

FLUX выполняет дополнительную обработку выбранных H3-кадров. В исходной схеме выбраны:

| Файл | Папка | Статус источника |
|---|---|---|
| `new_flux-2-klein-9b.safetensors` | `models/diffusion_models/` | Точный публичный источник этого файла из RH не подтверждён |
| `qwen_3_8b_fp8mixed.safetensors` | `models/text_encoders/` | [Каталог Comfy-Org для Klein 9B](https://huggingface.co/Comfy-Org/vae-text-encorder-for-flux-klein-9b/tree/main/split_files/text_encoders), тип CLIP = `flux2` |
| `flux2-vae.safetensors` | `models/vae/` | [Каталог VAE Comfy-Org](https://huggingface.co/Comfy-Org/vae-text-encorder-for-flux-klein-9b/tree/main/split_files/vae) |

Для точного повторения запросите у знакомого исходный `new_flux-2-klein-9b` и выбранные LoRA. Другой Klein с новым именем не станет тем же самым файлом. Если будет выбрана публичная замена, её нужно записать как отдельный вариант и проверить результат.

## LoRA из исходного JSON

Все находятся в `models/loras/`. Сохранённая сила указана для понимания экспорта, а не как универсальная рекомендация.

| Файл | Сила в экспорте | Где используется |
|---|---|---|
| `Pussy4nus_Epoch80.safetensors` | 0 | Видеоветвь / H3 карусели |
| `NSGIRL-MiniMax-H3-LoRA-By-MM744.safetensors` | 0 | Видеоветвь / H3 карусели |
| `Motion_Repair.safetensors` | 0 | Видеоветвь |
| `H3-GalaxyAce.safetensors` | 0,7 | H3 карусели |
| `Flux-2-Klein-9B-Detailed-Skin-LoRA.safetensors` | 1 | FLUX карусели |
| `flux2-klein-9b-Enhance-Realism-lora.safetensors` | 0,8 | FLUX карусели |
| `F2k-9B-Consistent-Image-Editing-LoRA.safetensors` | 0,5 | FLUX карусели |
| `FLUX.2-klein-base-9B_LoRa_by-AI_Characters_STYLE_SmartphoneSnapshotPhotoReality_v11_TRIGGER$snapshot photoV2$.safetensors` | 0,6 | FLUX карусели |

Для большей части этих точных имён публичные загрузки не подтверждены. Нужны файлы от автора или карточки конкретных версий. Исходные заметки содержат дополнительные ссылки, но не дают гарантии совпадения весов.

В наших отдельных кейсах эти LoRA не использовались. В полной схеме даже загрузчик с силой 0 может потребовать файл при проверке. Его нужно получить либо осознанно обойти через `Bypass`.

## Seed-VC: замена голоса

Нода устанавливается отдельно от её весов. Основные файлы в `models/TTS/Seed-VC/`:

- `DiT_seed_v2_uvit_whisper_base_f0_44k_bigvgan_pruned_ft_ema.pth`;
- `DiT_seed_v2_uvit_whisper_small_wavenet_bigvgan_pruned.pth`;
- `campplus_cn_common.bin`;
- `rmvpe.pt`.

Также нужны папки BigVGAN и `whisper-small` в `models/TTS/` со всеми файлами из [инструкции Seed-VC](https://github.com/billwuhao/ComfyUI_Seed-VC#model-download). Состав зависит от версии пакета. Эти модели автоматически не скачиваются.

T8 использует основной аудио-VAE H3. Отдельный LTX-checkpoint для него не нужен.

## DLSS и NVIDIA VSR

**DLSS:** кроме Python-пакета нужен отдельный runtime. На Linux в исходном пакете предусмотрены Wine, компоненты DirectX/Vulkan и NVIDIA DLL. Файлы размещаются по инструкции [ComfyUI-RH-DLSS5](https://github.com/RH-RunningHub/ComfyUI-RH-DLSS5), обычно в `models/dlss5/`. Установщик этого проекта не скачивает эти DLL и не настраивает Wine.

**VSR:** используется пакет [NVIDIA VFX nodes](https://github.com/Comfy-Org/Nvidia_RTX_Nodes_ComfyUI) и `nvidia-vfx`. Наличие ноды не подтверждает, что выбранная обработка уже выполнялась на вашем GPU. Проверяйте коротким примером после основной генерации.

## Что ещё не нужно скачивать

В этой версии нет отдельного второго H3-прохода, SeedVR2, Krea2 или отдельной LTX-модели озвучки. Нода `Separate AV Latent` разделяет совместные видео- и аудиоданные и сама по себе не означает, что нужна ещё одна генеративная модель.

Лицензии и доступ к сторонним весам определяются их авторами. Репозиторий хранит схемы и ссылки, а не распространяет веса.
