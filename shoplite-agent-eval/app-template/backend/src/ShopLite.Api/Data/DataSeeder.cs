using Microsoft.AspNetCore.Identity;
using ShopLite.Api.Domain;

namespace ShopLite.Api.Data;

public static class DataSeeder
{
    public static void Seed(ShopLiteDbContext db, IPasswordHasher<AppUser> hasher)
    {
        db.Database.EnsureCreated();
        if (db.Users.Any())
        {
            return;
        }

        var alice = CreateUser(hasher, "alice", "Alice123!", Roles.Customer);
        var bob = CreateUser(hasher, "bob", "Bob123!", Roles.Customer);
        var admin = CreateUser(hasher, "admin", "Admin123!", Roles.Admin);
        db.Users.AddRange(alice, bob, admin);

        var products = CreateProducts();
        db.Products.AddRange(products);
        db.SaveChanges();

        db.Orders.AddRange(
            CreateOrder(alice.Id, "SL-000001", new DateTime(2026, 9, 2, 10, 15, 0, DateTimeKind.Utc), (products[0], 1), (products[5], 2)),
            CreateOrder(alice.Id, "SL-000002", new DateTime(2026, 9, 20, 16, 40, 0, DateTimeKind.Utc), (products[12], 1)),
            CreateOrder(bob.Id, "SL-000003", new DateTime(2026, 9, 25, 8, 5, 0, DateTimeKind.Utc), (products[18], 3)));
        db.SaveChanges();
    }

    private static AppUser CreateUser(IPasswordHasher<AppUser> hasher, string username, string password, string role)
    {
        var user = new AppUser { Username = username, PasswordHash = string.Empty, Role = role };
        user.PasswordHash = hasher.HashPassword(user, password);
        return user;
    }

    private static Order CreateOrder(int userId, string number, DateTime createdAtUtc, params (Product Product, int Quantity)[] lines)
    {
        var subtotal = lines.Sum(l => l.Product.Price * l.Quantity);
        return new Order
        {
            UserId = userId,
            Number = number,
            CreatedAtUtc = createdAtUtc,
            Subtotal = subtotal,
            Discount = 0m,
            Total = subtotal,
            Lines = lines.Select(l => new OrderLine
            {
                ProductId = l.Product.Id,
                Quantity = l.Quantity,
                UnitPrice = l.Product.Price,
            }).ToList(),
        };
    }

    private static List<Product> CreateProducts() =>
    [
        new() { Name = "Chef's Knife", Category = "Kitchen", Price = 49.90m, Stock = 25, Description = "20 cm stainless steel blade." },
        new() { Name = "Cast Iron Skillet", Category = "Kitchen", Price = 39.50m, Stock = 12, Description = "Pre-seasoned 26 cm skillet." },
        new() { Name = "Bamboo Cutting Board", Category = "Kitchen", Price = 19.99m, Stock = 40, Description = "Large board with juice groove." },
        new() { Name = "French Press", Category = "Kitchen", Price = 29.00m, Stock = 18, Description = "1 L borosilicate glass." },
        new() { Name = "Spice Rack", Category = "Kitchen", Price = 24.75m, Stock = 9, Description = "Wall-mounted, 12 jars included." },
        new() { Name = "Desk Lamp", Category = "Office", Price = 34.99m, Stock = 30, Description = "Dimmable LED with USB port." },
        new() { Name = "Notebook A5", Category = "Office", Price = 6.50m, Stock = 200, Description = "Dotted pages, 160 sheets." },
        new() { Name = "Fountain Pen", Category = "Office", Price = 59.00m, Stock = 7, Description = "Medium nib, converter included." },
        new() { Name = "Monitor Stand", Category = "Office", Price = 44.90m, Stock = 15, Description = "Oak veneer, two levels." },
        new() { Name = "Desk Organizer", Category = "Office", Price = 17.30m, Stock = 22, Description = "Five compartments." },
        new() { Name = "Ergonomic Chair Cushion", Category = "Office", Price = 27.40m, Stock = 11, Description = "Memory foam seat cushion." },
        new() { Name = "Whiteboard", Category = "Office", Price = 64.00m, Stock = 5, Description = "90 x 60 cm magnetic board." },
        new() { Name = "Garden Hose", Category = "Garden", Price = 32.00m, Stock = 14, Description = "25 m with spray nozzle." },
        new() { Name = "Pruning Shears", Category = "Garden", Price = 21.90m, Stock = 26, Description = "Bypass blades, safety lock." },
        new() { Name = "Watering Can", Category = "Garden", Price = 15.50m, Stock = 33, Description = "Galvanised steel, 9 L." },
        new() { Name = "Herb Planter", Category = "Garden", Price = 23.00m, Stock = 3, Description = "Three-pot window planter." },
        new() { Name = "Garden Gloves", Category = "Garden", Price = 9.90m, Stock = 60, Description = "Breathable, size M." },
        new() { Name = "Bird Feeder", Category = "Garden", Price = 18.60m, Stock = 2, Description = "Hanging feeder with roof." },
        new() { Name = "The Pragmatic Gardener", Category = "Books", Price = 22.00m, Stock = 50, Description = "Paperback, 320 pages." },
        new() { Name = "Cooking for Two", Category = "Books", Price = 27.50m, Stock = 19, Description = "Hardcover, 180 recipes." },
        new() { Name = "Desk Lamp Bulb Pack", Category = "Office", Price = 12.00m, Stock = 45, Description = "Pack of 4 replacement bulbs." },
        new() { Name = "Lamp Shade", Category = "Office", Price = 16.80m, Stock = 13, Description = "Linen drum shade." },
        new() { Name = "Atlas of Small Islands", Category = "Books", Price = 35.00m, Stock = 8, Description = "Illustrated hardcover." },
        new() { Name = "Pocket Guide to Birds", Category = "Books", Price = 12.90m, Stock = 24, Description = "Field guide, 250 species." },
        new() { Name = "Compost Bin", Category = "Garden", Price = 79.00m, Stock = 4, Description = "300 L, recycled plastic." },
    ];
}
