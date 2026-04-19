from tqdm.asyncio import tqdm


async def tqdm_gather(*fs, return_exceptions=False, **kwargs):
    if not return_exceptions:
        return await tqdm.gather(*fs, **kwargs)

    async def wrap(f):
        try:
            return await f
        except BaseException as e:
            return e

    return await tqdm.gather(*map(wrap, fs), **kwargs)
