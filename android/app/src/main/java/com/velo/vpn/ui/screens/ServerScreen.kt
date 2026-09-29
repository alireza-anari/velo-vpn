package com.velo.vpn.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.velo.vpn.data.ServerDto
import com.velo.vpn.ui.Routes
import com.velo.vpn.ui.VeloViewModel
import com.velo.vpn.ui.components.FeatureRow
import com.velo.vpn.ui.components.PrimaryButton
import com.velo.vpn.ui.components.VeloCard
import com.velo.vpn.ui.components.VeloHeader
import com.velo.vpn.ui.theme.Muted
import com.velo.vpn.ui.theme.VeloPurple

@Composable
fun ServerScreen(nav: NavHostController, vm: VeloViewModel) {
    val state by vm.home.collectAsState()
    LaunchedEffect(Unit) { vm.refreshServers() }

    Scaffold { pad ->
        Column(
            Modifier.fillMaxSize().padding(pad).padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            VeloHeader(showBack = true, onBack = { nav.popBackStack() })
            Text("انتخاب سرور", fontSize = 29.sp, fontWeight = FontWeight.ExtraBold)
            FeatureRow(Icons.Default.Bolt, "بهترین سرور", "انتخاب خودکار بر اساس ظرفیت") {
                vm.selectServer(null)
                nav.popBackStack()
            }

            if (!state.premium) {
                VeloCard(Modifier.fillMaxWidth()) {
                    Text("در نسخه رایگان Velo بهترین سرور را خودکار انتخاب می‌کند.", fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(7.dp))
                    Text("با Premium می‌توانید کشور را خودتان انتخاب کنید.", color = Muted, fontSize = 12.sp)
                    Spacer(Modifier.height(12.dp))
                    PrimaryButton("ارتقا به Premium") { nav.navigate(Routes.Premium) }
                }
            } else {
                Text("سرورها", fontWeight = FontWeight.Bold, fontSize = 17.sp)
                if (state.servers.isEmpty()) {
                    Text("در حال دریافت سرورها...", color = Muted)
                }
                state.servers.forEach { server ->
                    ServerRow(server, selected = state.selectedServerId == server.id) {
                        if (!server.locked) {
                            vm.selectServer(server)
                            nav.popBackStack()
                        } else {
                            nav.navigate(Routes.Store)
                        }
                    }
                }
            }
            state.info?.let { Text(it, color = VeloPurple, fontSize = 12.sp) }
        }
    }
}

@Composable
private fun ServerRow(server: ServerDto, selected: Boolean, onClick: () -> Unit) {
    VeloCard(Modifier.fillMaxWidth(), onClick = onClick) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(flag(server.countryCode), fontSize = 27.sp)
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(server.name, fontWeight = FontWeight.Bold)
                if (server.city.isNotBlank()) Text(server.city, color = Muted, fontSize = 11.sp)
                if (!server.available) Text("موقتاً در دسترس نیست", color = MaterialTheme.colorScheme.error, fontSize = 11.sp)
            }
            if (server.tier == "vip") AssistChip(onClick = onClick, label = { Text("VIP") })
            else if (server.tier == "premium") AssistChip(onClick = onClick, label = { Text("Premium") })
            Spacer(Modifier.width(8.dp))
            RadioButton(selected = selected, onClick = if (server.locked || !server.available) null else onClick)
        }
    }
}

private fun flag(code: String): String = when (code.uppercase()) {
    "DE" -> "🇩🇪"; "TR" -> "🇹🇷"; "US" -> "🇺🇸"; "CA" -> "🇨🇦"; "NL" -> "🇳🇱"; "FR" -> "🇫🇷"; "GB" -> "🇬🇧"
    else -> "🌐"
}
