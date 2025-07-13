# 🚀 GUIDA SUPER SEMPLICE - Test GPS Digifly

## ⚡ ISTRUZIONI VELOCISSIME (3 MINUTI)

### 1️⃣ PREPARA IL COMPUTER (solo la prima volta)
```bash
pip3 install requests paho-mqtt
```

### 2️⃣ VAI NELLA CARTELLA
```bash
cd percorso/della/cartella/manufacturer
```

### 3️⃣ LANCIA IL TEST
```bash
./run_all_gps_tests.sh
```

**✅ FATTO! Il test partirà automaticamente sul server di produzione!**

---

## 📱 Cosa fa questo test?

Simula un dispositivo GPS Digifly che:
1. Si registra al server (come attivare un nuovo telefono)
2. Riceve username e password 
3. Invia la posizione GPS (Chamonix, Francia)

## 🎯 Cosa succederà quando lanci il test

Vedrai 4 test automatici:
```
=== Testing All 4 GPS Endpoints (PRODUCTION) ===
🔗 Production Endpoints:
   API: https://dg-dev.hikeandfly.app/api/v1
   MQTT: dg-mqtt.hikeandfly.app:8883

1. Testing MQTT Single GPS Point ✅
2. Testing MQTT Batch GPS Points ✅
3. Testing HTTP Single GPS Point ✅
4. Testing HTTP Batch GPS Points ✅

=== All Tests Complete ===
✅ If all tests passed, your integration is working correctly!
```

## ❓ Domande Frequenti

### "Devo modificare qualcosa?"
**NO!** È tutto già configurato per il server di produzione.

### "Cosa sono MQTT e HTTP?"
- **MQTT** = Per dispositivi IoT (batteria lunga)
- **HTTP** = Come navigare su internet
Non ti preoccupare, il test prova entrambi!

### "Il test è andato bene?"
Se vedi `✅ All tests completed successfully!` è tutto OK!

## 🆘 Se hai problemi

### Errore: "python3: command not found"
👉 Installa Python da python.org

### Errore: "No module named 'requests'"
👉 Esegui: `pip3 install requests paho-mqtt`

### Errore: "Permission denied"
👉 Esegui: `chmod +x run_all_gps_tests.sh`

### Altri errori
👉 Manda screenshot a Simone!

## 📂 Cosa c'è nella cartella

```
manufacturer/
├── run_all_gps_tests.sh      ← LO SCRIPT DA LANCIARE
├── GUIDA_ITALIANA.md          ← Questa guida
├── scripts/                   ← Script Python (non toccare)
└── examples/                  ← Esempi per programmatori
```

## 🎉 Riassunto

1. **Installa le librerie** (solo prima volta): `pip3 install requests paho-mqtt`
2. **Vai nella cartella**: `cd manufacturer`
3. **Lancia**: `./run_all_gps_tests.sh`
4. **Aspetta 30 secondi**
5. **Fatto!** Se vedi ✅ funziona tutto!

---

**💡 RICORDA**: Non devi capire come funziona, basta lanciare lo script e vedere che tutti i test passano con ✅

**🚁 Buon volo!**