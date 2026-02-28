# 外网访问部署指南

## 架构

```
用户 → Cloudflare → inv.runwith.top → Cloudflare Tunnel → aliyun_scheduler:nginx
      → frp 隧道 (port 8000) → macmini:8000 (FastAPI)
```

## 1. macmini (本机) - frpc 配置

已完成。frpc 配置文件 `/opt/homebrew/etc/frp/frpc.toml` 已添加 web proxy：

```toml
[[proxies]]
name = "web"
type = "tcp"
localIP = "127.0.0.1"
localPort = 8000
remotePort = 8000
```

重启: `brew services restart frpc`

## 2. aliyun_scheduler - Nginx 配置

将 `deploy/nginx-inv.conf` 复制到服务器：

```bash
scp deploy/nginx-inv.conf aliyun_scheduler:/etc/nginx/sites-available/inv.runwith.top
ssh aliyun_scheduler "ln -sf /etc/nginx/sites-available/inv.runwith.top /etc/nginx/sites-enabled/ && nginx -t && systemctl reload nginx"
```

## 3. aliyun_scheduler - Cloudflare Tunnel

在 Cloudflare Zero Trust Dashboard 添加 ingress 规则：

- Hostname: `inv.runwith.top`
- Service: `http://localhost:80`

或者编辑 tunnel config yaml:

```yaml
ingress:
  - hostname: inv.runwith.top
    service: http://localhost:80
  # ... 其他已有规则
```

## 4. Cloudflare DNS

在 Cloudflare DNS 面板中：
- 添加 CNAME 记录: `inv` → tunnel UUID `.cfargotunnel.com`
- 或通过 tunnel dashboard 自动配置

## 5. 验证

```bash
# 本地测试
curl http://localhost:8000/login

# 通过 frp 测试 (从 aliyun_scheduler)
curl http://127.0.0.1:8000/login

# 外网测试
curl https://inv.runwith.top/login
```

## 待解决: Aliyun 安全组

frpc 连接 aliyun_scheduler:7000 超时。需要在 Aliyun ECS 安全组中放开端口 7000 的入站规则：

- 协议: TCP
- 端口: 7000
- 授权对象: 0.0.0.0/0 (或限制为 macmini 公网 IP)

放开后重启 frpc: `brew services restart frpc`

## 安全说明

- Web 服务已配置 Token 认证 (WEB_AUTH_TOKEN)
- 未认证请求会重定向到 /login 页面
- API 请求返回 401
- Cookie 使用 httponly + samesite=lax
