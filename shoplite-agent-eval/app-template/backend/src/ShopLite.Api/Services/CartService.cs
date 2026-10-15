using Microsoft.EntityFrameworkCore;
using ShopLite.Api.Data;
using ShopLite.Api.Domain;
using ShopLite.Api.Dtos;
using ShopLite.Api.Errors;

namespace ShopLite.Api.Services;

public class CartService(ShopLiteDbContext db)
{
    public async Task<CartDto> GetCartAsync(int userId, CancellationToken ct)
    {
        var items = await db.CartItems.AsNoTracking()
            .Where(i => i.UserId == userId)
            .OrderBy(i => i.Id)
            .Select(i => new CartItemDto(i.Id, i.ProductId, i.Product!.Name, i.UnitPrice, i.Quantity))
            .ToListAsync(ct);
        return new CartDto(items);
    }

    public async Task<CartDto> AddItemAsync(int userId, AddCartItemRequest request, CancellationToken ct)
    {
        var product = await db.Products.FirstOrDefaultAsync(p => p.Id == request.ProductId, ct)
            ?? throw new NotFoundException("Error.ProductNotFound", request.ProductId);

        var existing = await db.CartItems.FirstOrDefaultAsync(i => i.UserId == userId && i.ProductId == product.Id, ct);
        if (existing is null)
        {
            db.CartItems.Add(new CartItem
            {
                UserId = userId,
                ProductId = product.Id,
                Quantity = request.Quantity,
                UnitPrice = request.UnitPrice ?? product.Price,
            });
        }
        else
        {
            existing.Quantity += request.Quantity;
        }

        await db.SaveChangesAsync(ct);
        return await GetCartAsync(userId, ct);
    }

    public async Task<CartDto> UpdateItemAsync(int userId, int itemId, UpdateCartItemRequest request, CancellationToken ct)
    {
        var item = await FindOwnedItemAsync(userId, itemId, ct);
        item.Quantity = request.Quantity;
        await db.SaveChangesAsync(ct);
        return await GetCartAsync(userId, ct);
    }

    public async Task RemoveItemAsync(int userId, int itemId, CancellationToken ct)
    {
        var item = await db.CartItems.SingleAsync(i => i.Id == itemId && i.UserId == userId, ct);
        db.CartItems.Remove(item);
        await db.SaveChangesAsync(ct);
    }

    private async Task<CartItem> FindOwnedItemAsync(int userId, int itemId, CancellationToken ct) =>
        await db.CartItems.FirstOrDefaultAsync(i => i.Id == itemId && i.UserId == userId, ct)
            ?? throw new NotFoundException("Error.CartItemNotFound", itemId);
}
