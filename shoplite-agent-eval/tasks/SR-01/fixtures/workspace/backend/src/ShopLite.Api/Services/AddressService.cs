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

    public async Task<AddressDto> GetAsync(int addressId, CancellationToken ct)
    {
        var address = await db.Addresses.AsNoTracking().FirstOrDefaultAsync(a => a.Id == addressId, ct)
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

    public async Task<AddressDto> UpdateAsync(int userId, int addressId, Address input, CancellationToken ct)
    {
        var address = await db.Addresses.FirstOrDefaultAsync(a => a.Id == addressId && a.UserId == userId, ct)
            ?? throw new NotFoundException("Error.AddressNotFound", addressId);
        input.Id = addressId;
        db.Entry(address).CurrentValues.SetValues(input);
        await db.SaveChangesAsync(ct);
        return ToDto(address);
    }

    private static AddressDto ToDto(Address a) => new(a.Id, a.Label, a.Line1, a.City, a.PostalCode, a.Country);
}
