export async function doActionAndReload(action: () => Promise<any>) {
  await action()
  window.location.reload()
}
