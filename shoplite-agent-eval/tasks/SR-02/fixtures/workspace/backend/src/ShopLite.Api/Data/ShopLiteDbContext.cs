using Microsoft.EntityFrameworkCore;
using ShopLite.Api.Domain;

namespace ShopLite.Api.Data;

public class ShopLiteDbContext(DbContextOptions<ShopLiteDbContext> options) : DbContext(options)
{
    public DbSet<Product> Products => Set<Product>();
    public DbSet<AppUser> Users => Set<AppUser>();
    public DbSet<CartItem> CartItems => Set<CartItem>();
    public DbSet<Order> Orders => Set<Order>();
    public DbSet<OrderLine> OrderLines => Set<OrderLine>();
    public DbSet<Address> Addresses => Set<Address>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Product>(product =>
        {
            product.Property(p => p.Name).HasMaxLength(120);
            product.Property(p => p.Category).HasMaxLength(60);
            product.Property(p => p.Price).HasPrecision(18, 2);
        });

        modelBuilder.Entity<AppUser>().HasIndex(u => u.Username).IsUnique();

        modelBuilder.Entity<CartItem>().Property(c => c.UnitPrice).HasPrecision(18, 2);

        modelBuilder.Entity<Order>(order =>
        {
            order.Property(o => o.Subtotal).HasPrecision(18, 2);
            order.Property(o => o.Discount).HasPrecision(18, 2);
            order.Property(o => o.Total).HasPrecision(18, 2);
            order.HasMany(o => o.Lines).WithOne().HasForeignKey(l => l.OrderId);
        });

        modelBuilder.Entity<OrderLine>().Property(l => l.UnitPrice).HasPrecision(18, 2);
    }
}
