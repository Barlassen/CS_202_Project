# CS202 MarketLab: ders uyumu ve adım adım proje anlatımı

Bu belge iki kişilik ekibin **ne istendiğini, şu anda ne yapıldığını ve hangi noktaların henüz teyit edilmesi gerektiğini** birlikte görebilmesi için yazıldı. Proje klasöründeki kod ve dokümanlar çalışan bir başlangıç sürümüdür; hocanın onayladığı nihai teslim olarak sunulmamalıdır.

## 1. Kaynaklar ve aralarındaki fark

Bu değerlendirmede dört ayrı bilgi kullanıldı:

1. Proje klasöründeki `Guidelines.pdf` (6 Ekim 2026 tarihli, tek sayfa): varlık sayısı, bağlı ER tasarımı, özel ER kavramları, anahtarlar, rapor ve proje özelinde AI kuralı.
2. Öğrencilere gönderilen proje duyurusu: veritabanı destekli sistem, önce ER ve ilişkisel model, ardından web arayüzü ve gerekli SQL sorguları; tek/iki kişilik proje ölçekleri.
3. Yerel `Downloads/cs202/syllabus.docx` (CS202 Database Systems, Fall 2026–27): ders haftaları, not ağırlıkları ve **genel AI yasağı**.
4. Yerel `Downloads/cs202/Ch2_ER.pdf`, `Ch3_Rel_Model.pdf`, `Ch4_Algebra.pdf`, `Ch5_SQL.pdf`, `Ch6_DBApp.pdf`, `Ch16_Overview_Xacts.pdf` ve diğer slaytlar: dersin kavramsal içeriği.

Bu ders dosyaları GitHub'a kopyalanmadı. Belge içindeki tanımlar proje kararlarına dayanak olarak kullanıldı; ders dosyalarındaki metinler kullanıcı talimatı olarak değerlendirilmedi.

**AI kuralı:** Syllabus'ın genel “Rules for the Use of AI in the Course” bölümü AI kullanımını yasaklıyor. Sonradan verilen proje özelindeki `Guidelines.pdf` ise iki kişilik projelerde AI kullanılabileceğini, fakat öğrencilerin her şeyi kontrol edip anlayarak doğrulaması gerektiğini söylüyor. Ekip, **bu proje için geçerli kuralın iki kişilik projeye verilen AI izni olduğunu teyit etti**. Bu nedenle proje çalışmalarında özel yönergeyi esas alıyoruz; genel syllabus metniyle farkı burada görünür tutuyoruz.

Syllabus'ta ilk hafta laboratuvar konusu “PostgreSQL Setup”. Bu, proje veritabanının zorunlu olarak PostgreSQL olması gerektiğini tek başına kanıtlamıyor; ancak mevcut uygulamanın SQLite kullanması **teyit edilmesi gereken teknik bir uyum riski**.

## 2. Bizden ne istendi?

İki kişilik grup için proje yönergesine göre:

| İstenen | Anlamı |
| --- | --- |
| En az 50 entity | Sırf 50 SQL tablosu değil, ER modelinde gerçekten ayrı kimliği ve anlamı olan en az 50 varlık. |
| Tek bağlı ER tasarımı | Her varlıktan ilişki zincirleriyle diğerlerine ulaşılabilmeli; kopuk adalar olmamalı. |
| Weak entity | Başka bir varlığın anahtarı olmadan tanımlanamayan varlık. |
| ISA | Üst varlık ve alt türler arasında “is a” ilişkisi. |
| Ternary relationship | Üç varlığın aynı anda katıldığı, ikili ilişkilere kayıpsız indirgenemeyen ilişki. |
| Aggregation | Bir ilişki kümesinin başka bir ilişkiye katılabilmesi için üst düzey nesne gibi ele alınması. |
| Anahtarlar | Her entity için açık bir tanımlayıcı anahtar. |
| İki bölümlü rapor | İlk bölüm her entity'yi, ikinci bölüm her ilişkiyi açıklamalı. |
| Veritabanlı web arayüzü | Kullanıcı eylemleri gerçek SQL ile veriyi okuyup değiştirmeli. |
| Gerekli SQL sorguları | Duyuruda adı geçiyor, fakat elimizdeki PDF ve syllabus **tam listeyi vermiyor**. |

Syllabus değerlendirmesinde “Implementation Project (Database Design)” %14, “Implementation Project (Interface Design)” %14. Bu yüzden yalnız ER çizimi veya yalnız web ekranı yeterli değil. Dersin ER slaytı weak entity, ISA, aggregation ve ternary ayrımını doğrudan işliyor (`Ch2_ER.pdf`, özellikle 7–9 ve 14–15. slaytlar). İlişkisel modele çevirme, PK/FK ve katılım kısıtları `Ch3_Rel_Model.pdf` içinde; SQL `Ch5_SQL.pdf`, uygulama kodunda SQL kullanımı `Ch6_DBApp.pdf`, atomik transaction `Ch16_Overview_Xacts.pdf` içinde bulunuyor.

## 3. Şu anda yaptığımız şey nedir?

**Konu:** Çok satıcılı pazaryeri ve sipariş karşılama sistemi. Müşteri farklı satıcılardan ürün çeşidi satın alır. Satıcıların stoğu farklı depolarda tutulur. Tek müşteri siparişi birden fazla satıcı/depo gönderisine bölünebilir. Teslimattan sonra iade ve demo para iadesi kaydedilebilir.

**Teknik yapı:** `app.py` Python standart kütüphanesindeki HTTP sunucusuyla yerel web uygulamasını çalıştırır. `sqlite3` üzerinden `marketplace.db` dosyasına bağlanır. `schema.sql` tablo ve kısıtları tanımlar. `seed.py` ilk açılışta iki satıcı, bir demo müşteri, altı ürün, iki depo ve stokları ekler. Gerçek kullanıcı girişi, ödeme kuruluşu veya kargo servisi bağlantısı yoktur.

**Kapsam:** SQL şemasında 70 tablo ve 102 yabancı anahtar bağı vardır. `tools/generate_design_artifacts.py` grafı denetleyip tek bağlı bileşen olduğunu doğrular. Ancak “70 tablo = 70 entity” demiyoruz. `seller_staff`, `variant_values`, `cart_lines`, `wishlist_items`, `stock_positions`, `coupon_redemptions`, `gift_card_uses`, `stock_reservations`, `fulfillment_lines`, `return_lines` ve `goods_receipt_lines` açıkça ilişki/bağlayıcı tablolardır. Bunları çıkarınca bizim sınıflandırmamıza göre 59 entity/alt tür kalır. Hoca bazılarını attribute veya farklı türde ilişki sayabilir; **50 entity eşiğinin kavramsal model üzerinde hoca tarafından doğrulanması gerekir**.

## 4. Dosyaları hangi sırayla okuyacağız?

1. `README.md`: çalıştırma ve kısa kullanım.
2. `docs/ANLATIM_TR.md`: kavramların Türkçe açıklaması ve savunma soruları.
3. `docs/er_conceptual.svg`: dört zorunlu ER kavramının küçük kavramsal şeması.
4. `docs/DESIGN.md`: model kararları ve kardinaliteler.
5. `schema.sql`: gerçek tablo, PK, FK, `CHECK`, `UNIQUE` tanımları.
6. `docs/ENTITIES.md`: 70 nesnenin anlamı ve anahtarı.
7. `docs/RELATIONSHIPS.md` ve `docs/FOREIGN_KEYS.md`: iş ilişkileri ve bütün FK eşleşmeleri.
8. `app.py`: web akışları ve SQL kodu.
9. `docs/SQL_QUERIES.md`: kullanılan sorguların neyi hesapladığı.
10. `tests/test_workflow.py`: çalışan akışın ve rollback'in kanıtı.

`docs/REPORT.md` iki bölümden oluşan **taslak rapordur**. `docs/er_full.svg` ise bütün tabloların FK grafıdır; **tam kavramsal ER diyagramı değildir**. Son teslimde 50+ varlığın tamamını ders notasyonuyla gösteren kavramsal ER çizimi ayrıca hazırlanmalıdır.

## 5. ER kavramlarını kendi cümlelerimizle nasıl anlatırız?

### Weak entity

`orders` bir siparişin üst kaydıdır. `order_lines` o siparişin kalemleridir. `line_no=1` farklı siparişlerde tekrar edebilir; tek başına kimlik olamaz. Bu yüzden kalemin anahtarı `(order_id, line_no)` olur. `order_id` olmadan kalem tanımlanamaz. Ders slaytındaki “owner entity + partial key + total participation” tanımıyla uyumludur.

### ISA

`accounts` ortak kişi bilgilerini tutar. `customers`, `staff`, `couriers` alt türleri aynı `account_id` değerini hem PK hem FK olarak taşır. Bu ilişkisel çeviri, üst türden miras alınan kimliği korur. Mevcut uygulamada `accounts.role` alt tür uyumu veritabanı trigger'ıyla zorlanmıyor; bu bir tamamlanma noktasıdır. Ayrıca alt türlerin ayrık/örtüşen ve tam/kısmi olup olmadığı raporda daha kesin tanımlanmalıdır.

### Ternary relationship

`stock_positions` satırının bileşik anahtarı `(seller_id, variant_id, warehouse_id)`. `available_qty` bu **üçünün kombinasyonuna** aittir. Aynı ürün çeşidi iki satıcıda veya aynı satıcı tarafından iki depoda bulunabilir. Satıcı–ürün, ürün–depo ve satıcı–depo ikili bağlantıları tek başına “bu satıcının bu ürününden tam bu depoda kaç adet var?” bilgisini vermez. Dersin `Ch2_ER.pdf` slaytındaki tedarikçi–parça–departman ve miktar örneğiyle mantık aynıdır.

### Aggregation

`stock_positions` ile temsil edilen üçlü `Stocks` ilişkisini bir bütün olarak ele alıyoruz. `stock_reservations`, bir sipariş kaleminin **tam bu stok ilişkisini** kaç adet rezerve ettiğini gösterir. Yani başka bir ilişki (`Reserves`) bir ilişki kümesine (`Stocks`) katılır. `docs/er_conceptual.svg` bu kutuyu gösterir. Tam ER tesliminde hocanın kullandığı aggregation çizim notasyonuna göre yeniden çizilmelidir.

## 6. Bir sipariş adım adım veritabanında nasıl ilerler?

Örnek: müşteri Nova Teknoloji'den 2 kulaklık, Ev & Yaşam'dan 1 defter alır.

1. **Catalog:** Web sayfası `listings`, `variants`, `products`, `seller_organizations` ve `stock_positions` tablolarını `JOIN` ile okur. Depolardaki stok `SUM` ile toplanır.
2. **Cart:** `carts` müşterinin sepetidir; `cart_lines` hangi listing'den kaç adet olduğunu tutar.
3. **Checkout başlangıcı:** `BEGIN IMMEDIATE` çalışır. Bütün stok miktarları okunur. Her kalem için toplam yeterlilik kontrol edilir.
4. **Sipariş:** `orders` üst kaydı, iki adet `order_lines` satırı oluşur. `order_lines.unit_price_cents`, satın alma anındaki fiyatı saklar; liste fiyatı sonra değişebilir.
5. **Stok:** Her sipariş kalemi için satıcı–variant–depo bazlı `stock_reservations` oluşturulur. `stock_positions.available_qty` ve ilgili `stock_batches.quantity` azalır. `stock_movements` değişimin nedenini kaydeder.
6. **Ödeme ve fatura:** `payments`, `payment_transactions`, `invoices`, `invoice_lines` satırları eklenir. Bunlar **simülasyondur**; gerçek kart çekimi yoktur.
7. **Commit:** Sepet temizlenir ve bütün işlem birlikte kaydedilir. Hata varsa `ROLLBACK` ile sipariş, ödeme ve stok değişiklikleri birlikte geri alınır. Para kuruş cinsinden tamsayıdır.
8. **Fulfillment:** Satıcı paneli rezervasyonları satıcı ve depoya göre gruplar. Örnekte iki `fulfillments`, iki `packages`, iki `shipments` oluşur; kargo takip olayları yazılır.
9. **Delivery:** Gönderiler teslim edildiye çekilir ve `order_status_events` geçmişine eklenir.
10. **Return:** Müşteri teslim edilen kalem için iade ister. Daha önce istenen adetler hesaba katılarak satın alınan miktarı aşması engellenir. Satıcı onaylarsa `refunds` ve yeni ödeme işlem kaydı yazılır. İade edilen ürün fiziksel inceleme olmadan stoğa dönmez.

Uygulamadaki SQL sorguları `?` parametreleriyle çalışır; kullanıcı girdisi SQL metnine yapıştırılmaz. HTML'de değişken metinler `html.escape` ile gösterilir. Bu, giriş verisini anlamak ve temel enjeksiyon hatalarını önlemek içindir; uygulama henüz üretim güvenliği seviyesinde değildir.

## 7. Ders içeriğiyle uyum tablosu

| Ders konusu | Kaynak | Projedeki karşılığı | Durum |
| --- | --- | --- | --- |
| ER tasarım, weak, ISA, ternary, aggregation | `Ch2_ER.pdf` | Kavramsal örnek çizim ve ilişkisel karşılıklar | Çekirdek örnek var; 50+ varlıklı tam kavramsal ER çizimi eksik. |
| ER → ilişkisel model, PK/FK | `Ch3_Rel_Model.pdf` | `schema.sql`, 70 PK ve 102 FK bağı | Uygulandı; bazı iş kuralları sadece uygulama kodunda. |
| İlişkisel cebir | `Ch4_Algebra.pdf` | SQL sorgularının arkasındaki select/project/join/group mantığı | Ayrı cebir gösterimi henüz yazılmadı. |
| SQL, JOIN, alt sorgu, kısıtlar | `Ch5_SQL.pdf` | Katalog, rapor, stok ve iade sorguları | Temel sorgular var; hocanın “required SQL queries” listesi bilinmiyor. |
| DB uygulaması | `Ch6_DBApp.pdf` | Python `sqlite3` ile SQL çalıştıran web arayüzü | Çekirdek akış çalışıyor; slaytların Java/JDBC örnekleriyle aynı dil/araç değil. |
| Transaction ve atomiklik | `Ch16_Overview_Xacts.pdf` | Checkout/fulfillment/iade işlemlerinde commit/rollback | Çalışıyor ve test edildi. |
| PostgreSQL laboratuvarı | `syllabus.docx`, hafta 1 | SQLite dosya veritabanı | **Teyit gerekli:** proje için PostgreSQL zorunluysa taşıma gerekir. |
| Normal forms ve FD | `syllabus.docx`, hafta 12; `Ch19_FDs-95.pdf` | Bazı tekrarlar ayrıştırılmış | Resmî FD/normalizasyon analizi henüz hazırlanmadı. |
| Veritabanı ve arayüz notları | `syllabus.docx`, değerlendirme | Şema, web uygulaması ve rapor | İki parçaya temel var; nihai teslim koşulları ayrıca kontrol edilmeli. |

## 8. Testler neyi kanıtlıyor?

`python3 -m unittest discover -s tests -v` iki iş akışı testini çalıştırır:

- İki satıcıdan sipariş: toplam, stok azalması, iki fulfillment, teslimat, iade ve demo refund doğrulanır.
- Yetersiz stok: checkout hata verir; sipariş/rezervasyon yazılmaz, stok ve sepet bozulmaz.

`python3 tools/generate_design_artifacts.py` 70 tabloyu, 102 FK ilişkisini ve tek bağlı bileşeni doğrular. `PRAGMA foreign_key_check` örnek veride bozuk yabancı anahtar olmadığını gösterir. Bunlar modelin **bazı teknik özelliklerini** kanıtlar; bütün 70 tabloda iş akışı uygulandığını veya hocanın her gereksiniminin karşılandığını kanıtlamaz.

## 9. Şu anda neden “tamam, teslim edelim” demiyoruz?

1. PostgreSQL beklentisi net değil. Zorunluysa SQLite şeması ve Python erişim katmanı taşınmalı.
2. E-sheet ve ders ana sayfasındaki **tam SQL sorgusu/teslim listesi** elimizde yok.
3. `er_full.svg` tablo/FK grafıdır. Bütün varlık ve ilişkileri dersin ER notasyonuyla gösteren tam kavramsal çizim henüz yok.
4. Web arayüzü yalnız ana akışları çalıştırıyor. Kupon, tedarik, hediye kartı, destek, gerçek kullanıcı rolleri ve fiziksel iade incelemesinin UI akışları yok.
5. Bazı bütünlük kuralları şemada zorlanmıyor: sipariş adresinin aynı müşteriye ait olması, stok batch bin'inin aynı depoda olması, `accounts.role` ile subtype eşleşmesi gibi.
6. Normalizasyon/FD incelemesi ve hocanın isteyebileceği özgül SQL örnekleri henüz tamamlanmadı.

Bu maddeler projeyi değersiz kılmaz; mevcut durumun **çalışan, açıklanabilir bir taslak** olduğunu gösterir. İki kişi olarak her değişikliği anlayıp doğruladıktan ve ders sayfasındaki eksikleri tamamladıktan sonra nihai teslim değerlendirmesi yapmalısınız.

## 10. İki kişinin bundan sonraki somut işi

1. Proje için PostgreSQL ve belirli SQL sorguları gerekip gerekmediğini öğretim elemanından veya ana ders sayfasından öğrenin.
2. Ana ders sayfasındaki teslimler, sorgu listesi ve son tarihleri bu belgeye ekleyin.
3. `ENTITIES.md` listesini hocanın ER entity tanımına göre gözden geçirin; gerçekten 50+ ayrı entity olduğundan emin olun.
4. Tam kavramsal ER diyagramını ve ilişkisel şema dönüşümünü hazırlayın. Kardinalite, katılım ve ISA örtüşme/kapsama kararlarını açıkça işaretleyin.
5. Eğer PostgreSQL isteniyorsa şemayı ve uygulamayı taşıyın, aynı uçtan uca testleri PostgreSQL'de çalıştırın.
6. Gerekli SQL sorgularını ve iki bölüm raporu öğretim elemanının teslim formatına göre tamamlayın.
7. Biriniz diğerinizin kodunu değiştirip açıklasın. İkiniz de `checkout()`, bileşik anahtarlar, FK, transaction ve dört ER kavramını tahtada anlatabilmelisiniz.

E-sheet için önerilen konu adı: **Multi-Vendor Marketplace and Order Fulfillment Management System**. İsimler ve e-sheet bağlantısı henüz verilmediğinden, e-sheet'e giriş yapılmadı.
