from sqlalchemy.ext.asyncio import AsyncSession

async def seed_database(session: AsyncSession):
    """
    Production Mode:
    Tüm mock/seed verileri arındırılmıştır.
    Sistem veritabanı boşken sıfır tesis, sıfır rampa ve sıfır randevu ile açılır.
    Kullanıcı ilk girişte dinamik olarak kendi tesisini ve rampalarını tanımlar.
    """
    pass
