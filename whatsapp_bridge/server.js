const { Client, LocalAuth } = require('whatsapp-web.js');
const QRCode = require('qrcode');
const express = require('express');

const app = express();
app.use(express.json());

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: { headless: true, args: ['--no-sandbox'] }
});

let isReady = false;
let currentQR = null;

client.on('qr', async (qr) => {
    console.log('QR kod güncellendi.');
    try {
        currentQR = await QRCode.toDataURL(qr);
    } catch (e) {
        console.error('QR üretme hatası:', e.message);
    }
});

client.on('ready', () => {
    isReady = true;
    currentQR = null;
    console.log('WhatsApp bağlantısı hazır!');
});

client.on('disconnected', () => {
    isReady = false;
    console.log('WhatsApp bağlantısı kesildi.');
});

client.initialize();

app.post('/send', async (req, res) => {
    const { to, message } = req.body;
    if (!isReady) {
        return res.status(503).json({ ok: false, error: 'WhatsApp henüz bağlı değil' });
    }
    if (!to || !message) {
        return res.status(400).json({ ok: false, error: 'to ve message zorunlu' });
    }
    try {
        await client.sendMessage(to, message);
        console.log(`Mesaj gönderildi -> ${to}`);
        res.json({ ok: true });
    } catch (e) {
        console.error('Gönderim hatası:', e.message);
        res.status(500).json({ ok: false, error: e.message });
    }
});

app.get('/status', (req, res) => {
    res.json({ ready: isReady, qr: currentQR });
});

app.listen(3001, () => {
    console.log('WhatsApp Bridge çalışıyor: http://localhost:3001');
});
