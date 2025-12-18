local claims = std.extVar('claims');

{
  identity: {
    traits: {
      email: claims.owner.user.email,
      name: {
        first: claims.owner.user.name,
        last: ''
      },
      oauth_connections: {
        notion: {
          connected: true,
          workspace_id: claims.workspace_id,
          workspace_name: claims.workspace_name
        }
      }
    }
  }
}
