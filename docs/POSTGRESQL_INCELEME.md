# PostgreSQL incelemesi ve test sonuçları

**21 Kasım 2026 · PostgreSQL 18.6.** İnceleme, SQL for Project tesliminde kullanılacak şema üzerinde yapıldı. Boş veritabanına kurulum ve ikinci kurulum başarılı oldu. Son şemada 79 tablo, 79 birincil anahtar ve 117 yabancı anahtar sayıldı. Hocanın istediği tablo ve ilişki kurulumu tamamlandı. Aşağıdaki iş akışı sonuçları, doğrudan PostgreSQL’e kayıt yazıldığında gözlenen davranışı anlatır. [SQL dosyası](../marketlab_postgres.sql) · [SQL kodunun anlatımı](POSTGRESQL_ANLATIM.md)

## İlk incelemede ne bozuluyordu?

| İlk sürümde doğrulanan durum | Yapılan değişiklik | Sonuç |
| --- | --- | --- |
| A satıcısından alınan X varyantı için B satıcısının Y varyantı rezerve edilebiliyordu. Aynı kalem yanlış satıcının sevkiyatına da eklenebiliyordu. | İlan kimliği sipariş kalemi, rezervasyon ve ilan arasında birleşik yabancı anahtarlarla bağlandı. Sevkiyat, o satıcı ve depodaki rezervasyonla karşılaştırıldı. | Yanlış satıcı veya varyant reddedildi. Doğru satıcının iki farklı deposundan rezervasyon kabul edildi. |
| 1 adet sipariş edilmiş kalem için 9 adet rezervasyon, sevkiyat ve iade kaydedilebiliyordu. | İşlem sonunda tam rezervasyon, satıcı/depo başına birikimli sevkiyat tavanı ve kalem başına birikimli aktif iade tavanı kontrol edildi. | Eksik ve fazla rezervasyon, fazla sevkiyat ve fazla aktif iade reddedildi. |
| Bir bağlantı müşteri alt türünü eklerken diğeri hesabı personel rolüne geçirebiliyordu. Ardından aynı kimlik iki alt türde bulunabiliyordu. | Alt türün sabit rolü ile hesap kimliği tek yabancı anahtar olarak doğrulandı. | Her iki işlem sırası da denendi. Çakışan işlem yabancı anahtar hatası verdi. |

## Hangi durumlar denendi?

- Beş adetlik bir kalem iki depoya 3 + 2 bölündü. Bir depoda birden fazla kısmi sevkiyat yapılabildi. Aynı deponun payını aşan sevkiyat reddedildi.
- Kalemdeki ilanı değiştirme, rezervasyonu başka kaleme taşıma, rezervasyon silme ve rezervasyon tablosunu boşaltma işlemleri denendi. İşlem sonunda dengesiz kalan sipariş reddedildi. Kalem ve rezervasyonların aynı işlemde birlikte düzeltilmesi kabul edildi.
- Sevkiyat başlığındaki satıcı veya depo sonradan değiştirildiğinde mevcut satırlar yeniden denetlendi. Reddedilmiş bir iade talebini tekrar etkinleştirmek miktar tavanını aştığında işlem reddedildi.
- Ayrı bağlantılarla rol değişikliği/alt tür ekleme, sevkiyat/sevkiyat ve iade/iade çakışmaları denendi. Miktar testlerinde `READ COMMITTED` altında kural ihlali, `REPEATABLE READ` altında serileştirme hatası gözlendi. İki bağlantının da sınırı aşarak kaydettiği bir sonuç oluşmadı.

## Doğrudan SQL ile hâlâ kabul edilen dört durum

| İş kuralı | İlk bakışta çalışan kontrol | Son incelemede kaydedilen örnek | Eksik kontrol |
| --- | --- | --- | --- |
| Para iadesi | Ödeme ve iade talebi aynı siparişe ait. | 100 kuruş tahsilata karşılık, **reddedilmiş** bir talebe 200 kuruş onaylı geri ödeme yazıldı. | Talebin onayı ve başarılı iadelerin toplamının tahsil edilmiş tutarı aşmaması. |
| Fiziksel stok | Rezerve edilen ürün ve miktar siparişle eşleşiyor. | Kullanılabilir miktarı **0** olan depo pozisyonundan 1 adet ayrıldı. | Rezervasyon ile kullanılabilir stok düşümünün aynı işlemde, yeterli bakiye kontrol edilerek yapılması. SQLite demosu bu düşümü uygulama kodunda yapıyor. |
| Teslim sonrası iade | Aktif iadelerin toplamı sipariş miktarını aşmıyor. | Durumu `placed` olan, sevkiyat satırı bulunmayan sipariş için 1 adet iade kabul edildi. | İade açılırken teslim durumunun ve iade edilebilir teslim miktarının doğrulanması. |
| Kupon kullanım sınırı | Aynı sipariş aynı kuponu yalnızca bir kez kullanabiliyor. | `max_uses = 1` olan kupon iki ayrı siparişte kullanıldı. | Siparişler arasındaki toplam kullanımın kupon limitine göre kontrol edilmesi. |

Bu dört gözlem şemanın kurulum sonucundan bağımsızdır. Örneğin stok testinde sipariş miktarıyla rezervasyon toplamı tam eşleşmiştir. Testin gösterdiği eksik, o birimin depo bakiyesinden ayrılabilmesidir. Önceki pgAdmin çiziminde de `stock_reservations.listing_id` ve müşteri alt türünün `role` sütunu görünmüyordu. Güncel fiziksel şema için teslim SQL’iyle oluşturulan veritabanı esas alınır.

## Testleri yeniden çalıştırma

PostgreSQL istemcisi olan bir makinede, Python 3 ve Psycopg 3 ile aşağıdaki komutları proje kökünde çalıştır. Bağlantı için libpq’nun standart ortam değişkenleri (`PGDATABASE`, `PGHOST`, `PGPORT`, `PGUSER`) veya yerel bağlantı ayarları kullanılır. Bağlantı kullanıcısının test veritabanında şema oluşturma yetkisi olmalıdır.

```sh
python -m pip install "psycopg[binary]>=3,<4"
python tests/verify_postgres.py
```

Test kendine ait benzersiz bir şema açar, SQL dosyasını burada iki kez çalıştırır, örnek kayıtları ekler ve sonunda bu şemayı kaldırır. Olumlu örnekler ile reddedilmesi gereken işlemler otomatik denetlenir. Son bölümdeki dört bilinen davranış ayrıca raporlanır. İleride bunlardan biri düzeltilirse test o örneğin artık reddedildiğini bildirir. [Doğrulama programı](../tests/verify_postgres.py)


## Diyagram sürümleri

- [Güncel daldaki kavramsal ER diyagramı](MarketLab_ER_Diagram.pdf) on bir sayfada ilişkileri ve gösterimlerini açıklar.
- [Önceki pgAdmin çizimi](er/archive/PG_ER_Diagram.pgerd) son kısıt değişikliklerinden önceki fiziksel şemayı gösterir. Özellikle rezervasyondaki ilan bağlantısı ve alt türlerin rol sütunları karşılaştırılırken bu sürüm farkı dikkate alınmalıdır.
- [Tek sayfalık ER çizimi](er/archive/MarketLab_ER_Diagram-Uygar_Kocakir-Barlas_Sen.pdf) ekip adlarıyla kaydedilmiş önceki PDF kopyasıdır.
