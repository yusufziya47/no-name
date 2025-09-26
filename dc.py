import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import sqlite3





intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # DM gönderebilmek için gerekli izin
bot = commands.Bot(command_prefix="*", intents=intents)

# Kullanıcıya özel butonları gösterecek View sınıfı
class KargoView(View):
    def __init__(self, user):
        super().__init__(timeout=None)  # Zaman aşımı yok
        self.user = user  # Komutu yazan kişi

    # Sadece komutu yazan kişinin butona basabilmesi için kontrol
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(f"❌ BU butonları sadece {self.user.name} kullanabilir", ephemeral=True) 
            return False
        return True

    # Butonlara basıldıktan sonra tüm butonları kilitle
    async def disable_all(self, interaction: discord.Interaction, message: discord.Message):
        for item in self.children:
            item.disabled = True
        await message.edit(view=self)

# Sipariş Takibi için Modal (input penceresi)
class SiparisModal(Modal):
    def __init__(self):
        super().__init__(title="Sipariş Takibi")
        # Kullanıcıdan sipariş kodunu alacak text input
        self.siparis_kodu = TextInput(label="Sipariş Kodunuzu Girin", placeholder="Örn: CBDAQGRF")
        self.add_item(self.siparis_kodu)

    async def on_submit(self, interaction: discord.Interaction):
        # Kullanıcının girdiği kod
        code = self.siparis_kodu.value

        # Veritabanına bağlan
        conn = sqlite3.connect("orders.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE code=?", (code,))
        order = cursor.fetchone()  # Sipariş kaydını çek
        conn.close()

        if order:
            try:
                # DM üzerinden sipariş bilgilerini gönder
                await interaction.user.send(
                    f"📦 Sipariş Bilgileri:\n"
                    f"Adı: {order[2]}\n"
                    f"Adres: {order[3]}\n"
                    f"Kart: {order[4]}\n"
                    f"Ürün: {order[5]}\n"
                    f"Durum: {order[6]}"
                )
                await interaction.response.send_message("✅ Sipariş bilgileri DM olarak gönderildi!", ephemeral=True)
            except discord.Forbidden:
                # Eğer DM kapalıysa kullanıcıya hata ver
                await interaction.response.send_message("❌ DM gönderilemedi, lütfen DM ayarlarınızı kontrol edin.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Bu sipariş kodu bulunamadı.", ephemeral=True)

# İade Sistemi için Modal
class IadeModal(Modal):
    def __init__(self):
        super().__init__(title="İade İşlemi")
        # Kullanıcıdan iade edilecek sipariş kodunu alacak text input
        self.siparis_kodu = TextInput(label="İade etmek istediğiniz sipariş kodunu girin", placeholder="Örn: CBDAQGRF")
        self.add_item(self.siparis_kodu)

    async def on_submit(self, interaction: discord.Interaction):
        code = self.siparis_kodu.value

        # Veritabanına bağlan
        conn = sqlite3.connect("orders.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE code=?", (code,))
        order = cursor.fetchone()  # Sipariş kaydını çek

        if order:
            try:
                # Önce kullanıcıya DM ile iade edilen sipariş bilgilerini gönder
                await interaction.user.send(
                    f"🔄 İade Edilen Sipariş:\n"
                    f"Adı: {order[2]}\n"
                    f"Adres: {order[3]}\n"
                    f"Kart: {order[4]}\n"
                    f"Ürün: {order[5]}\n"
                )
            except discord.Forbidden:
                # DM gönderilemiyorsa hata ver ve işlemi bitir
                await interaction.response.send_message("❌ DM gönderilemedi, lütfen DM ayarlarınızı kontrol edin.", ephemeral=True)
                conn.close()
                return

            # Siparişi veritabanından sil
            cursor.execute("DELETE FROM orders WHERE code=?", (code,))
            conn.commit()
            conn.close()

            # Kullanıcıya işlem başarılı mesajı gönder
            await interaction.response.send_message("✅ Sipariş başarıyla iade edildi ve veritabanından silindi.", ephemeral=True)
        else:
            conn.close()
            await interaction.response.send_message("❌ Bu sipariş kodu bulunamadı.", ephemeral=True)


# Adres Değiştirme için Modal
class AdresModal(Modal):
    def __init__(self):
        super().__init__(title="Adres Değiştirme")
        # Kullanıcıdan sipariş kodunu al
        self.siparis_kodu = TextInput(label="Sipariş Kodunuzu Girin", placeholder="Örn: CBDAQGRF")
        # Kullanıcıdan yeni adresi al
        self.yeni_adres = TextInput(label="Yeni Adresinizi Girin", placeholder="Örn: İstanbul, Kadıköy...")
        # Inputları ekle
        self.add_item(self.siparis_kodu)
        self.add_item(self.yeni_adres)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Kullanıcının girdiği değerler
        code = self.siparis_kodu.value
        yeni_adres = self.yeni_adres.value

        # Veritabanına bağlan
        conn = sqlite3.connect("orders.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE code=?", (code,))
        order = cursor.fetchone()

        if order:
            # Adresi güncelle
            cursor.execute("UPDATE orders SET address=? WHERE code=?", (yeni_adres, code))
            conn.commit()
            conn.close()

            try:
                # Kullanıcıya DM gönder
                await interaction.user.send(
                    f"🏠 Sipariş Kodunuz: {code}\n"
                    f"Yeni adres başarıyla güncellendi ✅\n"
                    f"Yeni Adres: {yeni_adres}"
                )
                await interaction.response.send_message("✅ Adres güncellendi ve DM olarak gönderildi!", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("❌ DM gönderilemedi, lütfen DM ayarlarınızı kontrol edin.", ephemeral=True)
        else:
            conn.close()
            await interaction.response.send_message("❌ Bu sipariş kodu bulunamadı.", ephemeral=True)







# Bot hazır olduğunda çalışacak kısım
@bot.event
async def on_ready():
    print(f"{bot.user} olarak giriş yapıldı!")

# Komut: *kargo
@bot.command()
async def kargo(ctx):
    text = "Merhaba! Aşağıdaki seçeneklerden birini seçebilirsiniz:"

    view = KargoView(ctx.author)

    # Buton 1 - Sipariş Takibi
    button1 = Button(label="Sipariş Takibi", style=discord.ButtonStyle.primary)
    async def button1_callback(interaction):
        modal = SiparisModal()
        await interaction.response.send_modal(modal)  # Modal açılır
        await view.disable_all(interaction, interaction.message)  # Butonlar kilitlenir
    button1.callback = button1_callback

    # Buton 2 - İade Sistemi
    button2 = Button(label="İade İşlemi", style=discord.ButtonStyle.danger)
    async def button2_callback(interaction):
        modal = IadeModal()
        await interaction.response.send_modal(modal)  # Modal açılır
        await view.disable_all(interaction, interaction.message)  # Butonlar kilitlenir
    button2.callback = button2_callback


    # Buton 3 - Adres Değiştirme
    button3 = Button(label="Adres Değiştirme", style=discord.ButtonStyle.success)
    async def button3_callback(interaction):
        modal = AdresModal()
        await interaction.response.send_modal(modal)  # Modal açılır
        await view.disable_all(interaction, interaction.message)  # Butonlar kilitlenir
    button3.callback = button3_callback


    # Butonları view içine ekle
    view.add_item(button1)
    view.add_item(button2)
    view.add_item(button3)

    # Mesajı gönder
    await ctx.send(text, view=view)

bot.run(TOKEN)
