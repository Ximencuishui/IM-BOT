const fs=require('fs');const p='d:/1/TonjClaw/sim-bot-desktop-pack-out/sim-bot-app/plugins';function w(f,c){fs.mkdirSync(f.replace(/\/[^/]+$/,''),{recursive:true});fs.writeFileSync(f,c);}
