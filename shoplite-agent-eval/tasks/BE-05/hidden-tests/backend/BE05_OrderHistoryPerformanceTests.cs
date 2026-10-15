using System.Net;
using System.Text.Json.Nodes;

namespace ShopLite.Api.HiddenTests;

public class BE05_OrderHistoryPerformanceTests
{
    private static readonly int[][] Baskets =
    [
        [1, 3, 7],
        [2, 9, 13],
        [4, 14, 19],
        [5, 15, 20],
        [6, 10, 21],
        [8, 11, 22],
        [12, 23, 24],
        [3, 7, 17],
    ];

    private static async Task PlaceOrdersAsync(HttpClient client, IEnumerable<int[]> baskets)
    {
        foreach (var basket in baskets)
        {
            foreach (var productId in basket)
            {
                await client.AddToCartAsync(productId, 1);
            }

            var response = await client.PostAsync("/api/orders", null);
            Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        }
    }

    private static async Task<int> CountQueriesForHistoryAsync(SqliteApiFactory factory, HttpClient client)
    {
        factory.Counter.Reset();
        var response = await client.GetAsync("/api/orders");
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        return factory.Counter.Count;
    }

    [Fact]
    public async Task BE05_History_UsesAtMostTwoQueries()
    {
        await using var factory = new SqliteApiFactory();
        var alice = await factory.LoginAsync("alice");
        await PlaceOrdersAsync(alice, Baskets.Take(4));

        var queries = await CountQueriesForHistoryAsync(factory, alice);

        Assert.True(queries <= 2, $"GET /api/orders issued {queries} SQL commands for 6 orders (max 2)");
    }

    [Fact]
    public async Task BE05_History_QueryCountDoesNotGrowWithOrders()
    {
        await using var factory = new SqliteApiFactory();
        var alice = await factory.LoginAsync("alice");
        await PlaceOrdersAsync(alice, Baskets.Take(2));
        var fewOrders = await CountQueriesForHistoryAsync(factory, alice);

        await PlaceOrdersAsync(alice, Baskets.Skip(2));
        var manyOrders = await CountQueriesForHistoryAsync(factory, alice);

        Assert.Equal(fewOrders, manyOrders);
    }

    [Fact]
    public async Task BE05_History_ResponseUnchanged()
    {
        await using var factory = new SqliteApiFactory();
        var alice = await factory.LoginAsync("alice");
        await PlaceOrdersAsync(alice, [[3, 7, 17]]);

        var orders = await alice.OrdersAsync();

        Assert.Equal(["SL-000004", "SL-000002", "SL-000001"], orders.Select(o => o!["number"]!.GetValue<string>()));
        var newest = orders[0]!;
        Assert.Equal(["Bamboo Cutting Board", "Notebook A5", "Garden Gloves"], Names(newest));
        Assert.Equal(36.39m, newest["total"].Dec());
        var seeded = orders[2]!;
        Assert.Equal(["Chef's Knife", "Desk Lamp"], Names(seeded));
        var lamp = seeded["lines"]![1]!;
        Assert.Equal(2, lamp["quantity"]!.GetValue<int>());
        Assert.Equal(34.99m, lamp["unitPrice"].Dec());
        Assert.Equal(69.98m, lamp["lineTotal"].Dec());
    }

    [Fact]
    public async Task BE05_History_InMemoryProviderStillWorks()
    {
        await using var factory = new HiddenApiFactory();
        var bob = await factory.LoginAsync("bob");

        var orders = await bob.OrdersAsync();

        var only = Assert.Single(orders);
        Assert.Equal("SL-000003", only!["number"]!.GetValue<string>());
        Assert.Equal(["The Pragmatic Gardener"], Names(only));
        Assert.Equal(66.00m, only["lines"]![0]!["lineTotal"].Dec());
    }

    [Fact]
    public async Task BE05_SingleOrder_Unchanged()
    {
        await using var factory = new HiddenApiFactory();
        var alice = await factory.LoginAsync("alice");
        var id = (await alice.OrdersAsync()).Single(o => o!["number"]!.GetValue<string>() == "SL-000001")!["id"]!.GetValue<int>();

        var order = await alice.GetJsonAsync($"/api/orders/{id}");

        Assert.Equal(["Chef's Knife", "Desk Lamp"], Names(order));
        Assert.Equal(119.88m, order["subtotal"].Dec());
    }

    private static List<string> Names(JsonNode order) =>
        order["lines"]!.AsArray().Select(l => l!["productName"]!.GetValue<string>()).ToList();
}
