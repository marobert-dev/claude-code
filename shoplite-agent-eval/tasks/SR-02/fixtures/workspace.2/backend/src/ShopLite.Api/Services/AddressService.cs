using Microsoft.EntityFrameworkCore;
using ShopLite.Api.Data;
using ShopLite.Api.Domain;
using ShopLite.Api.Dtos;
using ShopLite.Api.Errors;

namespace ShopLite.Api.Services;

public class AddressService(ShopLiteDbContext db)
{
    public async Task<IReadOnlyList<AddressDto>> ListAsync(int userId, CancellationToken ct) =>
        await db.Addresses.AsNoTracking()
            .Where(a => a.UserId == userId)
            .OrderBy(a => a.Label)
            .Select(a => new AddressDto(a.Id, a.Label, a.Line1, a.City, a.PostalCode, a.Country))
            .ToListAsync(ct);

    public async Task<AddressDto> GetAsync(int userId, int addressId, CancellationToken ct)
    {
        // SECURITY: IDOR — any signed-in customer can read any address by id; filter on the caller's user id and answer 404 otherwise (high).
        var address = await db.Addresses.AsNoTracking().FirstOrDefaultAsync(a => a.Id == addressId && a.UserId == userId, ct)
            ?? throw new NotFoundException("Error.AddressNotFound", addressId);
        return ToDto(address);
    }

    public async Task<AddressDto> CreateAsync(int userId, AddressRequest request, CancellationToken ct)
    {
        var address = new Address
        {
            UserId = userId,
            Label = request.Label.Trim(),
            Line1 = request.Line1.Trim(),
            City = request.City.Trim(),
            PostalCode = request.PostalCode.Trim(),
            Country = request.Country.ToUpperInvariant(),
        };
        db.Addresses.Add(address);
        await db.SaveChangesAsync(ct);
        return ToDto(address);
    }

    public async Task<AddressDto> UpdateAsync(int userId, int addressId, AddressRequest request, CancellationToken ct)
    {
        var address = await db.Addresses.FirstOrDefaultAsync(a => a.Id == addressId && a.UserId == userId, ct)
            ?? throw new NotFoundException("Error.AddressNotFound", addressId);
        // SECURITY: mass assignment — SetValues copies every client-supplied field including UserId; map the allowed fields from a request DTO instead (high).
        address.Label = request.Label.Trim();
        address.Line1 = request.Line1.Trim();
        address.City = request.City.Trim();
        address.PostalCode = request.PostalCode.Trim();
        address.Country = request.Country.ToUpperInvariant();
        await db.SaveChangesAsync(ct);
        return ToDto(address);
    }

    private static AddressDto ToDto(Address a) => new(a.Id, a.Label, a.Line1, a.City, a.PostalCode, a.Country);
}
