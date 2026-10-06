# MarketLab: iki kişilik ekip için Türkçe anlatım

Bu dosya, projeyi savunurken akışı kendi cümlelerinizle anlatabilmeniz için hazırlandı. Ezberlemek yerine `schema.sql` ve `app.py` içindeki ilgili satırları açıp akışı takip edin. İngilizce iki bölümlü rapor taslağı `REPORT.md` içindedir; bütün 70 nesnenin tek tek tanımı `ENTITIES.md`, bütün 102 yabancı anahtar bağı `FOREIGN_KEYS.md` içindedir.

## 1. Sistem hangi problemi çözüyor?

Birden çok bağımsız satıcı aynı pazaryerinde ürün çeşidi listeler. Müşteri farklı satıcılardan tek sipariş verebilir. Her satıcının ürünü farklı depolarda olabilir. Sipariş verildiğinde doğru satıcının doğru depodaki stoğu ayrılır. Ardından satıcı/depo bazında gönderiler hazırlanır; teslimattan sonra iade istenebilir. Rapor ekranı satış ve stok durumunu SQL ile özetler.

Örneğin bir müşteri Nova Teknoloji'den kulaklık ve Ev & Yaşam'dan defter aldığında **tek müşteri siparişi** oluşur, fakat **iki fulfillment/gönderi** oluşabilir. Bu ayrım veri modelinin merkezidir.

## 2. Dosyalar ne yapıyor?

- `schema.sql`: Tablolar, birincil/yabancı anahtarlar, `CHECK` ve `UNIQUE` kuralları. Tasarımın kalıcı veri kısmı.
- `seed.py`: İlk açılışta iki satıcı, altı ürün, depolar ve örnek stokları oluşturur.
- `app.py`: Yerel HTTP sunucusu, HTML sayfaları, SQL sorguları ve sipariş işlemleri.
- `static/style.css`: Ekranın görünümü.
- `docs/er_conceptual.svg`: Özel ER kavramlarının kavramsal çizimi.
- `docs/er_full.svg`: Bütün tablo bağlantılarının yakınlaştırılabilir çizimi.
- `tests/test_workflow.py`: Siparişten iadeye uçtan uca akış ve yetersiz stok kontrolü.

Çalıştırma: proje klasöründe `python3 app.py`; sonra `http://127.0.0.1:8000`. Python dışında kurulum gerekmiyor. Veriler `marketplace.db` dosyasında tutulur.

## 3. En önemli kavramlar

### Entity ve key

*Entity*, sistemde ayrı kimliği olan şeydir: müşteri, ürün, satıcı, depo, sipariş gibi. *Primary key* bir kaydı tek başına ayırt eder. Örneğin `orders.order_id` her sipariş için farklıdır. *Foreign key* başka bir tablonun anahtarına işaret eder; `orders.customer_id` siparişin müşterisini gösterir. `PRAGMA foreign_keys = ON` bağlantı başına bu denetimi etkinleştirir.

### Weak entity

`order_lines` tablosundaki `line_no` yalnız başına benzersiz değildir: her siparişin 1 numaralı kalemi olabilir. Bu nedenle anahtar **`(order_id, line_no)`** olur. Sipariş silinirse kalem kendi başına anlamlı değildir. ER diyagramındaki çift dikdörtgen bunu gösterir.

### ISA

`accounts` ortak kişi bilgilerini taşır. `customers`, `staff`, `couriers` bu üst varlığın özelleşmiş türleridir. Alt tablodaki `account_id`, hem birincil anahtar hem de `accounts` tablosuna yabancı anahtardır. Bu sayede aynı isim/e-posta ortak tabloda bir kez tutulur. Demo rolleri ayrı varsayar; veritabanında rol/alt tür uyumunu doğrulayan ek trigger henüz yoktur.

### Ternary relationship

`stock_positions` anahtarı **`(seller_id, variant_id, warehouse_id)`**. Bu üçlü, *hangi satıcının hangi ürün çeşidinden hangi depoda ne kadar stoğu var?* sorusunu yanıtlar. Stok miktarı yalnız ürüne veya yalnız depoya ait değildir; tam üçlü kombinasyona aittir. Üç ayrı ikili bağlantı bunu yeterince açık ifade edemez.

### Aggregation

`Seller — Stocks — Variant — Warehouse` üçlü ilişkisinin tamamını tek bir üst düzey nesne gibi düşünürüz. `stock_reservations`, bir `order_line` ile bu **tam stok konumu** arasında “şu kadar ayırdı” ilişkisi kurar. Sadece ürün kimliğini saklamak yetmezdi; satıcı ve depo bilgisi de gereklidir. `stock_reservations` bu yüzden iki bileşik bağlantı taşır: sipariş kalemine `(order_id, line_no)` ve stok konumuna `(seller_id, variant_id, warehouse_id)`.

## 4. Sipariş verme işlemi adım adım

1. Müşteri `cart_lines` ile seçtiği listing ve miktarı sepete ekler.
2. `checkout()` `BEGIN IMMEDIATE` ile yazma işlemini başlatır. SQLite bu sırada başka bir yazıcının aynı stoğu harcamasını engeller.
3. Her satır için `stock_positions` okunur. Miktar bir depoda yetmezse birden çok depoya bölünebilir. Bir satırda toplam yeterli stok yoksa **hiçbir sipariş kaydı yazılmadan** hata döner.
4. `orders` ve `(order_id, line_no)` anahtarlı `order_lines` oluşturulur. O anki fiyat kaleme kopyalanır; sonra listing fiyatı değişse bile sipariş tarihi doğru kalır.
5. Her ayrılan depo için `stock_reservations` eklenir, `stock_positions.available_qty` ve `stock_batches.quantity` düşer, `stock_movements` denetim kaydı yazılır.
6. Demo `payments` ve `payment_transactions` satırları, `invoices` ve `invoice_lines` satırları oluşturulur. Gerçek banka/kart işlemi yapılmaz.
7. Sepet temizlenir ve `COMMIT` çalışır. Herhangi bir adım hata verirse `ROLLBACK` bütün değişiklikleri geri alır.

Para `float` yerine kuruş cinsinden tamsayı tutulur. Örneğin `249900` kuruş = `₺2,499.00`.

## 5. Gönderi ve iade

Seller panelindeki **Fulfill & ship**, bir siparişi satıcı/depo grubuna ayırır. Her grup için `fulfillments`, `fulfillment_lines`, `packages`, `shipments` ve `tracking_events` kayıtları oluşur. **Mark delivered**, gönderileri ve siparişi teslim edildi durumuna geçirir, durum geçmişi ekler.

Teslim edilen siparişin bir kalemi için müşteri iade açabilir. Sistem daha önce reddedilmemiş iadelerin miktarını toplar ve sipariş edilen miktarı aşmasına izin vermez. Seller panelindeki **Approve & refund**, gerçek para transferi yapmadan `refunds` ve `payment_transactions` kayıtlarını oluşturur. İade edilen ürün hemen satılabilir stoğa eklenmez; önce fiziksel inceleme gerekir. `return_inspections` bunun için şemada vardır, ancak arayüz akışı henüz uygulanmamıştır.

## 6. SQL raporları

**Catalog** sorgusu listing, variant, product ve seller tablolarını birleştirir. Depoların stok toplamını `SUM` ve `GROUP BY` ile hesaplar. `LEFT JOIN` stok sıfır olsa bile listeyi gösterir.

**Revenue by seller**, sipariş kalemlerinde saklanan fiyatı kullanır. `COUNT(DISTINCT order_id)` aynı satıcıdan aynı siparişte iki kalem olsa da sipariş sayısını bir sayar. Bu gösterge brüt satış toplamıdır; iade ve komisyon düşmez.

**Low stock**, stok konumunun `available_qty` değerini aynı üçlünün `reorder_point` değeriyle karşılaştırır. **Top products** satılan adetleri toplar. **Return requests** durum başına sayım yapar. Gerçek SQL metinleri `SQL_QUERIES.md` içindedir.

## 7. Neden 70 tablo var?

Yönerge iki kişilik proje için en az 50 **entity** istiyor; duyuru da yaklaşık 50–100 tablo hedefi veriyor. Şemada 70 tablo ve 102 yabancı anahtar bağlantısı var. Bazı tablolar (`seller_staff`, `stock_reservations` gibi) aslında ilişki tablosudur; bu yüzden 70 tablonun hepsini kavramsal entity diye saymıyoruz. En muhafazakâr listemizde 11 ilişki tablosunu çıkardıktan sonra 59 adlandırılmış entity/alt tür kalıyor. Hoca bazı nesneleri attribute olarak yorumlayabilir; teslimden önce kavramsal modelinizi dersin ER notasyonuna göre gözden geçirin.

Alanlar: kimlik/satıcı, katalog, alışveriş/kampanya, stok/tedarik, sipariş/ödeme, gönderi, iade/destek. Şemadaki her nesnenin tanımı ve anahtarı `ENTITIES.md` dosyasında. Tabloların hepsi yabancı anahtar grafiğinde aynı bağlı bileşene ulaşıyor.

## 8. Şu anda ne tamam, ne tamam değil?

**Çalışan web akışları:** katalog arama, sepet, sipariş, stok düşümü/rezervasyon, demo ödeme ve fatura, çoklu satıcı gönderisi, teslimat, iade isteği/onayı, SQL raporları.

**Şeması olup tam ekranı olmayan alanlar:** kuponlar, hediye kartları, satın alma siparişleri, depoya mal kabul, destek mesajları, kullanıcı girişi/rol izinleri ve fiziksel iade incelemesi. Projeyi hocaya bunlar çalışıyormuş gibi anlatmayın. Bunlar final kapsamına girerse ayrıca tamamlanmalı.

## 9. Savunmada gelebilecek sorular

1. **Neden `order_lines` ayrı?** Bir sipariş birden çok ürün içerir; kalem fiyatı ve miktarı ayrıca tutulur.
2. **Neden fiyat `order_lines` içinde de var?** Sipariş anındaki fiyat tarihsel veridir; güncel listing fiyatı değişebilir.
3. **Üçlü ilişki neden gerekli?** Miktar tek tek satıcı, ürün veya depoya değil bunların birleşimine aittir.
4. **Aggregation nerede?** `stock_reservations`, sipariş kalemini `stock_positions` ilişkisinin tamamına bağlar.
5. **Bir müşteri tek siparişte farklı satıcılardan ürün alınca ne olur?** Tek `orders`, iki veya daha çok `order_lines`, satıcı/depo bazında farklı `fulfillments` ve `shipments`.
6. **Stok yetmezse ne olur?** İşlem hata verir ve rollback ile sipariş/ödeme/stok değişikliklerinin hiçbiri kalmaz.
7. **SQL injection nasıl önleniyor?** Kullanıcı girdileri `?` parametreleriyle SQL'e bağlanır, HTML çıktısı `html.escape` ile yazılır.
8. **Bu gerçek e-ticaret uygulaması mı?** Hayır; kimlik doğrulama, gerçek ödeme ve kargo entegrasyonu olmayan yerel ders demosudur.

## 10. İki kişinin çalışma önerisi

Bir kişi ER/şema/rapor ve SQL kısıtlarını, diğeri web akışları/testleri ilk turda inceleyebilir. Ardından rolleri değiştirin: herkes diğerinin kısmında bir değişiklik yapıp nedenini açıklasın. Değerlendirmede seçili parçalar ayrıntılı sorulacağı için ikiniz de `checkout()`, bileşik anahtarlar, yabancı anahtarlar ve dört özel ER kavramını gösterebilmelisiniz.
