document.addEventListener("DOMContentLoaded", () => {
  // Xử lý thêm vào giỏ hàng
  document.querySelectorAll('form[id^="add-to-cart-"]').forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const formData = new FormData(form);
      const response = await fetch("/add_to_cart", {
        method: "POST",
        body: formData,
      });
      const result = await response.json();
      alert(result.message || result.error);
    });
  });

  // Xử lý đăng ký
  const registerForm = document.querySelector("#register-form");
  if (registerForm) {
    registerForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const formData = new FormData(registerForm);
      const response = await fetch("/register", {
        method: "POST",
        body: formData,
      });
      const result = await response.json();
      const messageEl = document.querySelector("#message");
      if (response.ok) {
        messageEl.textContent = result.message;
        messageEl.classList.add("text-green-600");
      } else {
        messageEl.textContent = result.error;
        messageEl.classList.add("text-red-600");
      }
    });
  }

  // Xử lý đăng nhập
  const loginForm = document.querySelector("#login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const formData = new FormData(loginForm);
      const response = await fetch("/login", {
        method: "POST",
        body: formData,
      });
      const result = await response.json();
      const messageEl = document.querySelector("#message");
      if (response.ok) {
        messageEl.textContent = result.message;
        messageEl.classList.add("text-green-600");
        setTimeout(() => (window.location.href = "/"), 1000);
      } else {
        messageEl.textContent = result.error;
        messageEl.classList.add("text-red-600");
      }
    });
  }

  // Xử lý quên mật khẩu
  const resetForm = document.querySelector("#reset-form");
  if (resetForm) {
    resetForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const formData = new FormData(resetForm);
      const response = await fetch("/reset-password", {
        method: "POST",
        body: formData,
      });
      const result = await response.json();
      const messageEl = document.querySelector("#message");
      if (response.ok) {
        messageEl.textContent = result.message;
        messageEl.classList.add("text-green-600");
      } else {
        messageEl.textContent = result.error;
        messageEl.classList.add("text-red-600");
      }
    });
  }

  // Xử lý reset mật khẩu
  const resetConfirmForm = document.querySelector("#reset-confirm-form");
  if (resetConfirmForm) {
    resetConfirmForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const formData = new FormData(resetConfirmForm);
      const response = await fetch(resetConfirmForm.action, {
        method: "POST",
        body: formData,
      });
      const result = await response.json();
      const messageEl = document.querySelector("#message");
      if (response.ok) {
        messageEl.textContent = result.message;
        messageEl.classList.add("text-green-600");
        setTimeout(() => (window.location.href = "/login"), 1000);
      } else {
        messageEl.textContent = result.error;
        messageEl.classList.add("text-red-600");
      }
    });
  }

  // Xử lý form địa chỉ
  const deliveryForm = document.querySelector("#delivery-form");
  if (deliveryForm) {
    deliveryForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const formData = new FormData(deliveryForm);
      const response = await fetch("/delivery", {
        method: "POST",
        body: formData,
      });
      if (response.ok) {
        window.location.href = "/checkout";
      } else {
        const result = await response.json();
        alert(result.error);
      }
    });
  }

  // Xử lý thanh toán
  const checkoutForm = document.querySelector("#checkout-form");
  if (checkoutForm) {
    checkoutForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const response = await fetch("/checkout", {
        method: "POST",
      });
      const result = await response.json();
      if (response.ok) {
        alert("Purchase successful! Order ID: " + result.order_id);
        window.location.href = "/";
      } else {
        alert("Error: " + result.error);
      }
    });
  }
});
