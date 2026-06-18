部署说明
========

1. 将发卡端提供的 `activation_public.pem` 公钥文件放入此目录
2. 确保 `.env` 中的 `ACTIVATION_PUBLIC_KEY_PATH` 指向 `./keys/activation_public.pem`

如暂无公钥，可在 `.env` 中设置 `SKIP_PRODUCT_SETUP=1` 跳过授权验证。