# ZeroMQ Transport Security

This document describes the transport security landscape for ZeroMQ deployments. It is a general reference for developers and operators who need to understand what protection ZeroMQ provides by default, what additional mechanisms exist, and how to choose among them. It does not prescribe a single correct answer for every deployment. Each environment has different threat models, operational constraints, and policy requirements.

---

## 1. The baseline: plain ZeroMQ

By default, a ZeroMQ socket offers no authentication, no encryption, and no integrity protection at the transport layer. The bytes on the wire are sent as plain data. Any peer that can open a connection to the bound address can participate in the socket pattern: a REQ client can send requests, a SUB client can subscribe and receive published messages, a PUSH endpoint can feed a PULL peer, and so on. There is no built-in check that the remote party is who you expect, no guarantee that intermediaries cannot read or alter traffic, and no cryptographic proof that a message arrived unmodified.

What this means in practice depends on where the socket is bound and who can reach that address. On a shared host, any local process that is permitted by the operating system to connect to a TCP port or open a Unix domain socket path may be able to interact with a plain ZeroMQ endpoint unless something outside ZeroMQ restricts access. On a network, any host that routing and firewalls allow to reach the port can do the same. Plain ZeroMQ does not distinguish between a trusted application and an arbitrary one; reachability is effectively permission to speak the protocol.

The plain baseline is often acceptable when the communication path is already constrained by other means. Examples include a dedicated machine with no untrusted local users, a loopback-only bind where only processes on the same host can connect and the host itself is trusted, or a controlled management network where access is limited by VLANs, firewalls, and physical isolation. It may also be acceptable for non-sensitive telemetry on an internal network where confidentiality is not required and misuse is handled operationally rather than cryptographically.

The plain baseline becomes unacceptable when the socket is exposed on a network that untrusted parties can reach, when the host runs workloads from different trust domains, when messages carry credentials or control commands, or when regulatory or organisational policy requires encryption and authenticated peers. In those cases, relying on "nobody will find the port" or "our LAN is private" shifts security to network perimeter assumptions that may not hold after a misconfiguration, a compromised laptop on the LAN, or a container escape. Plain ZeroMQ is not a defect; it is an explicit design choice to keep the core library small and to let deployments layer security as needed. The risk is in using it without recognising that the layer is absent.

---

## 2. ZeroMQ CURVE

ZeroMQ includes a built-in security mechanism called CURVE. It is specified in RFC 25 of the ZeroMQ specification family and is implemented using libsodium's Curve25519 elliptic-curve Diffie-Hellman primitives. CURVE provides mutual authentication between peers, encryption of traffic after the handshake, and forward secrecy for session keys derived during that handshake. It does not depend on TLS, OpenSSL, or X.509 certificate hierarchies.

In CURVE-enabled deployments, both sides of a connection hold Curve25519 key pairs: a public key and a secret key. The server's long-term public key must be known to clients before they connect, distributed through a channel you trust separately from the ZeroMQ connection itself. Clients present their own keys during the handshake; the server can be configured to accept only clients whose public keys are listed in an allowed set, or to use a mechanism that maps keys to identities according to your policy. Once the handshake completes, application frames are encrypted for that session. A new session uses new ephemeral material, which is where forward secrecy comes from: compromise of long-term keys does not by itself decrypt past session traffic.

CURVE fits into ZeroMQ's architecture at the ZMQ security protocol layer above the transport. Application code still uses the same socket types and message patterns; security is negotiated when connections are established. What CURVE protects against includes passive eavesdropping on the wire, trivial injection of frames by parties who do not possess acceptable keys, and undetected tampering of ciphertext in transit under normal threat models for symmetrically encrypted channels. What it does not protect against includes compromise of endpoints after decryption, bugs in message parsing above the transport layer, denial of service from peers who complete handshakes legitimately, and misuse of the application protocol by an authenticated but malicious client.

Operational requirements deserve honest attention. You must generate and store server and client key material safely. You must distribute the server's public key to every client through a path that attackers cannot silently replace. If you maintain an allow-list of client public keys, onboarding and revocation become ongoing key-management tasks. Rotating server keys requires coordinated updates on clients. CURVE is native to ZeroMQ and avoids external proxies, but correct deployment is not automatic: a CURVE socket with permissive client acceptance or a public key distributed over an insecure channel provides a false sense of safety.

The normative specification for CURVE is published at https://rfc.zeromq.org/spec/25/

---

## 3. TLS wrapping

An alternative to CURVE is to terminate TLS outside the ZeroMQ application using a proxy or tunnel. In this model, ZeroMQ continues to use plain TCP between the application process and a local proxy endpoint, while the proxy opens a TLS-protected TCP connection to a peer proxy on the remote side, which in turn speaks plain TCP to the remote ZeroMQ process. Common tools for this pattern include stunnel, nginx in stream mode, and similar TLS-terminating forwarders. The TLS layer is handled by OpenSSL or another TLS implementation according to the proxy's configuration.

The trade-offs are structural rather than cryptographic at the framing level. TLS wrapping reuses organisational investment in certificate authorities, renewal workflows, hardware security modules, and compliance language that explicitly names TLS. Auditors and security policies that mandate TLS on the wire may be satisfied without modifying ZeroMQ application source code, because the application still sees ordinary TCP. You gain a mature ecosystem for cipher suite control, certificate expiry monitoring, and integration with enterprise identity practices when client certificates are used at the TLS layer.

The costs are operational complexity and an extra moving part in the data path. Every ZeroMQ endpoint that must be protected needs a correctly configured proxy, health monitoring, and alignment between proxy ports and application bind addresses. Certificate management becomes a parallel lifecycle: issuance, distribution, renewal, and revocation are your responsibility, and a expired or mismatched certificate breaks connectivity in ways that can be harder to diagnose than a CURVE handshake failure. Latency and throughput may be affected by the additional hop and TLS record processing. Mutual authentication at the TLS layer is only as strong as your certificate policy; a server that does not request client certificates authenticates the server to the client but not necessarily the client to the server unless you add that requirement explicitly.

TLS wrapping does not change how ZeroMQ serialises messages inside the tunnel. Application-level concerns remain unchanged. The tunnel protects the TCP bytestream between proxies; it does not replace thoughtful design of who may invoke which logical operations once messages are delivered.

---

## 4. Unix domain sockets

ZeroMQ can bind and connect to Unix domain socket paths in addition to TCP addresses. A Unix domain socket is a kernel-mediated inter-process communication endpoint identified by a filesystem path on a single machine. Access control is enforced by file permissions and ownership on that path, and by the operating system's process isolation rules. No encryption is applied to data moving through a Unix domain socket; payloads are visible to the kernel and to sufficiently privileged local actors in the same way as any local IPC.

This choice is appropriate when all communicating processes run on one host, when trust boundaries are expressed adequately through Unix permissions and separate user accounts, and when confidentiality against local passive attackers is not required. Binding to a path with restrictive permissions allows only selected users or groups to connect. Moving from a world-readable or overly permissive path to a tightly controlled one is a common hardening step for local services.

The limitations are geographic and cryptographic. Unix domain sockets do not cross machine boundaries. They offer no protection against a malicious process running as the same user that owns the socket, against root-equivalent actors on the host, or against physical memory attacks. They also do not help when a component must later be split across hosts without redesigning the transport.

Compared with binding plain ZeroMQ to localhost TCP, Unix domain sockets often provide clearer intent and sometimes better performance for local IPC. Localhost TCP still transits the network stack and is typically reachable by any local process unless additional firewall rules on the loopback interface are applied, which many installations do not configure. A Unix socket path with mode 0600 and ownership by a dedicated service account is an explicit admission control list at the filesystem layer. Neither localhost TCP nor Unix domain sockets encrypt traffic; the difference is primarily how connection eligibility is enforced on a single machine.

---

## 5. Choosing between the options

Decision-making should start from where sockets live, who must reach them, and what happens if an unauthorised party connects successfully.

For network-facing ZeroMQ traffic between hosts, plain TCP without additional protection is appropriate only when outer layers already provide equivalent guarantees and you accept the consequences if those layers fail. For most networked deployments that carry non-public data or control plane traffic, some form of authenticated encryption on the wire is expected. CURVE is a natural starting point when you want security integrated with ZeroMQ, minimal extra infrastructure, and key-based trust without a certificate authority. It rewards teams comfortable with long-term key distribution and allow-lists rather than annual certificate renewal ceremonies.

TLS wrapping deserves consideration when policy or existing operations mandate TLS specifically, when client and server certificates are already issued for other services and can be reused, or when a security team prefers to standardise on one TLS toolchain across protocols. It is less attractive when adding and operating proxies per service is burdensome relative to enabling CURVE in the socket options, or when certificate churn would dominate maintenance.

Unix domain sockets fit single-machine compositions where processes are colocated, filesystem permissions align with your trust model, and encryption would add little because the primary threat is remote network access rather than unrelated local users. They pair naturally with service managers that start workers under dedicated accounts and create runtime directories with controlled modes.

Plain TCP bound only to the loopback interface remains in use for local development and for tightly controlled appliances. It is weaker than Unix domain sockets for expressing least privilege on a shared multi-user host because any local process can often connect to 127.0.0.1 unless separately restricted. Operators should treat loopback binding as convenience, not as a complete access control story, whenever untrusted code can run on the same machine.

No option removes the need to think about firewalls, segmentation, and monitoring. Transport choice complements those controls; it does not replace them.

---

## 6. What none of these options address

Transport security establishes who is on the other end of the wire and whether bytes were protected in transit according to the mechanism's threat model. It does not, by itself, solve the full security problem of a distributed application.

Application-level authentication answers a different question than transport peer authentication. CURVE or TLS can confirm that a connection belongs to a key or certificate you recognise, but the application may still need to know which user or service role initiated a particular request, especially when proxies, connection pooling, or shared workers break a one-to-one mapping between connections and operators.

Authorisation determines whether an authenticated party may perform a specific action. A fully authenticated client might still be forbidden from issuing destructive commands, reading sensitive topics, or publishing to control sockets. Those rules belong in application logic or a dedicated policy layer; encrypting the channel does not infer them.

Input validation remains essential. Malformed frames, unexpected multipart structures, oversized payloads, and semantic nonsense can crash parsers, exhaust memory, or trigger undefined behaviour in consumers. Cryptography on the wire does not make untrusted content safe to parse without limits and schema discipline.

Denial of service is likewise not solved by encryption. A legitimate peer with a valid key or certificate can flood requests, subscribe to high-rate publishers, or hold connections open in patterns that degrade availability. Rate limiting, resource caps, and operational monitoring address availability; transport security does not.

Treat transport protection as necessary where confidentiality and peer authentication matter on the path between hosts, and as insufficient for a secure system overall. Design authentication, authorisation, validation, and resilience at the message and service level in addition to whatever wraps the TCP or Unix socket underneath.

---

## 7. References

- ZeroMQ CURVE specification: https://rfc.zeromq.org/spec/25/
- ZeroMQ security chapter (ZGuide): https://zguide.zeromq.org/docs/chapter5/
- libsodium documentation: https://doc.libsodium.org/
- stunnel documentation: https://www.stunnel.org/docs.html
