namespace ShopLite.Api.Errors;

public abstract class AppException(int statusCode, string titleKey, string detailKey, object[] detailArgs)
    : Exception(detailKey)
{
    public int StatusCode { get; } = statusCode;
    public string TitleKey { get; } = titleKey;
    public string DetailKey { get; } = detailKey;
    public object[] DetailArgs { get; } = detailArgs;
}

public sealed class NotFoundException(string detailKey, params object[] detailArgs)
    : AppException(StatusCodes.Status404NotFound, "Error.NotFound.Title", detailKey, detailArgs);

public sealed class BusinessRuleException(string detailKey, params object[] detailArgs)
    : AppException(StatusCodes.Status400BadRequest, "Error.BusinessRule.Title", detailKey, detailArgs);

public sealed class InvalidCredentialsException()
    : AppException(StatusCodes.Status401Unauthorized, "Error.Unauthorized.Title", "Error.InvalidCredentials", []);
