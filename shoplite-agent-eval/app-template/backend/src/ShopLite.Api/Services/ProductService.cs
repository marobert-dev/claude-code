using Microsoft.EntityFrameworkCore;
using ShopLite.Api.Data;
using ShopLite.Api.Domain;
using ShopLite.Api.Dtos;
using ShopLite.Api.Errors;

namespace ShopLite.Api.Services;

public class ProductService(ShopLiteDbContext db)
{
    public async Task<PagedResult<ProductSummaryDto>> SearchAsync(ProductQuery query, CancellationToken ct)
    {
        var products = db.Products.AsNoTracking();

        if (!string.IsNullOrWhiteSpace(query.Search))
        {
            var term = query.Search.Trim().ToLower();
            products = products.Where(p => p.Name.ToLower().Contains(term));
        }

        if (!string.IsNullOrWhiteSpace(query.Category))
        {
            products = products.Where(p => p.Category == query.Category);
        }

        var totalCount = await products.CountAsync(ct);
        var items = await products
            .OrderBy(p => p.Name)
            .ThenBy(p => p.Id)
            .Skip((query.Page - 1) * query.PageSize)
            .Take(query.PageSize)
            .Select(p => new ProductSummaryDto(p.Id, p.Name, p.Category, p.Price, p.Stock > 0))
            .ToListAsync(ct);

        var totalPages = (int)Math.Ceiling(totalCount / (double)query.PageSize);
        return new PagedResult<ProductSummaryDto>(items, query.Page, query.PageSize, totalCount, totalPages);
    }

    public async Task<IReadOnlyList<string>> GetCategoriesAsync(CancellationToken ct) =>
        await db.Products.AsNoTracking()
            .Select(p => p.Category)
            .Distinct()
            .OrderBy(c => c)
            .ToListAsync(ct);

    public async Task<ProductDto> GetAsync(int id, CancellationToken ct)
    {
        var product = await db.Products.AsNoTracking().FirstOrDefaultAsync(p => p.Id == id, ct)
            ?? throw new NotFoundException("Error.ProductNotFound", id);
        return ToDto(product);
    }

    public async Task<ProductDto> CreateAsync(ProductUpsertRequest request, CancellationToken ct)
    {
        var product = new Product { Name = request.Name, Category = request.Category };
        Apply(product, request);
        db.Products.Add(product);
        await db.SaveChangesAsync(ct);
        return ToDto(product);
    }

    public async Task<ProductDto> UpdateAsync(int id, ProductUpsertRequest request, CancellationToken ct)
    {
        var product = await db.Products.FirstOrDefaultAsync(p => p.Id == id, ct)
            ?? throw new NotFoundException("Error.ProductNotFound", id);
        Apply(product, request);
        await db.SaveChangesAsync(ct);
        return ToDto(product);
    }

    private static void Apply(Product product, ProductUpsertRequest request)
    {
        product.Name = request.Name.Trim();
        product.Description = request.Description.Trim();
        product.Category = request.Category.Trim();
        product.Price = request.Price;
        product.Stock = request.Stock;
    }

    private static ProductDto ToDto(Product p) => new(p.Id, p.Name, p.Description, p.Category, p.Price, p.Stock);
}
