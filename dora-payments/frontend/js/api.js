// SmartWatch & DORA Universal Payments - Unified API Client with Offline Demo Failover
const API_BASE = "/api/v1";

class DoraPaymentsAPI {
  static isOffline = false;
  static mockBalance = 50000; // Rs. 500.00 default demo wallet
  static mockPin = "1234";

  static async request(endpoint, options = {}) {
    if (this.isOffline) {
      return this.mockHandler(endpoint, options);
    }

    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {})
    };
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const json = await res.json();
      if (json.ok === false) {
        throw json.error || { message: "Payment request failed" };
      }
      return json.data;
    } catch (err) {
      console.warn("[DORA API] Serverless backend unavailable, switching to built-in simulation mode:", err);
      this.isOffline = true;
      return this.mockHandler(endpoint, options);
    }
  }

  static mockHandler(endpoint, options = {}) {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        if (endpoint === "/wallet") {
          resolve({ balance_paise: this.mockBalance, currency: "INR" });
        } else if (endpoint === "/wallet/topup") {
          const body = JSON.parse(options.body || "{}");
          this.mockBalance += (body.amount_paise || 50000);
          resolve({ balance_paise: this.mockBalance });
        } else if (endpoint === "/payments") {
          const body = JSON.parse(options.body || "{}");
          const txnId = "txn_" + Math.random().toString(36).substring(2, 10);
          resolve({
            txn_id: txnId,
            amount_paise: body.amount_paise,
            merchant_name: body.merchant_name || "Dora Cyber Cafe",
            state: "INITIATED"
          });
        } else if (endpoint.includes("/authorize")) {
          const body = JSON.parse(options.body || "{}");
          if (body.pin === this.mockPin) {
            resolve({
              state: "SUCCESS",
              receipt: {
                auth_code: "AUTH_" + Math.floor(100000 + Math.random() * 900000),
                timestamp: new Date().toISOString()
              }
            });
          } else {
            reject({ code: "INVALID_PIN", message: "Incorrect PIN. Default demo PIN is 1234" });
          }
        } else if (endpoint.includes("/cancel")) {
          resolve({ state: "CANCELLED" });
        } else {
          resolve({ ok: true });
        }
      }, 200);
    });
  }

  static async getWallet() {
    return this.request("/wallet");
  }

  static async topUpWallet(amountPaise) {
    return this.request("/wallet/topup", {
      method: "POST",
      body: JSON.stringify({ amount_paise: amountPaise })
    });
  }

  static async createPayment({ amountPaise, merchantName, merchantVpa, method, description }) {
    const idempotencyKey = "idemp_" + Math.random().toString(36).substring(2, 12);
    return this.request("/payments", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({
        amount_paise: amountPaise,
        merchant_name: merchantName,
        merchant_vpa: merchantVpa,
        payment_method: method || "WALLET",
        description: description
      })
    });
  }

  static async authorizePayment(txnId, pin) {
    return this.request(`/payments/${txnId}/authorize`, {
      method: "POST",
      body: JSON.stringify({ pin })
    });
  }

  static async cancelPayment(txnId) {
    return this.request(`/payments/${txnId}/cancel`, {
      method: "POST"
    });
  }
}

window.DoraAPI = DoraPaymentsAPI;
