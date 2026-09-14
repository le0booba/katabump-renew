## 🚀 katabump Auto-Renewal (GitHub Actions)

This is an automated script based on GitHub Actions designed to automatically log in and renew [katabump](https://dashboard.katabump.com) applications on a scheduled basis.

⚠️ Cloudflare protection is active. Low-quality datacenter nodes may fail to pass the challenge. It is recommended to use cleaner nodes, such as [B2proxy Residential Proxy](https://www.b2proxy.com/signup?code=0F5133).

━━━━━━━━━━━━━━━━━━━━━━

🔐 Secrets Configuration Guide

| Secret Name        | Required? | Description                                       |
|--------------------|-----------|---------------------------------------------------|
| KATABUMP_EMAIL     | ✅ Yes    | katabump login email                              |
| KATABUMP_PASSWORD  | ✅ Yes    | katabump login password                           | 
| NODE_LINK          | ❌ No     | Proxy link, e.g., vless:// vmess:// tuic:// hysteria2:// anytls:// socks5:// |
| TG_BOT_TOKEN       | ❌ No     | Telegram Bot Token (used to send notifications)    |
| TG_CHAT_ID         | ❌ No     | Telegram Chat ID (User or Group ID to receive notifications) |

━━━━━━━━━━━━━━━━━━━━━━
### Proxy Format (Ensure the node works properly in v2rayN)

`NODE_LINK` supports the complete share link of any of the following proxy protocols (defaults to direct connection if left blank):

- **VLESS**: `vless://uuid@server:port?security=reality&sni=...&type=ws&...`
- **VMess**: `vmess://base64encoded...`
- **Trojan**: `trojan://password@server:port?sni=...&type=ws&...`
- **tuic**: `tuic://uuid:password@server:port...`
- **anytls**: `anytls://uuid@server:port...`
- **hysteria2**: `hysteria2://base64@server:port...`
- **SOCKS5**: `socks5://user:pass@server:port` or `socks://user:pass@server:port`

### Notes
- Try to use a clean node to avoid getting blocked by Cloudflare protection.
- Adjust the cron schedule to trigger one day before your service's expiration date.
