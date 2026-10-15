export type LoadState<T> = { status: 'loading' } | { status: 'error' } | { status: 'success'; data: T };
