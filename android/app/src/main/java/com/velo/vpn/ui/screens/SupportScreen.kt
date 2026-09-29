package com.velo.vpn.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.velo.vpn.ui.AccountViewModel
import com.velo.vpn.ui.CommerceViewModel
import com.velo.vpn.ui.Routes
import com.velo.vpn.ui.components.PrimaryButton
import com.velo.vpn.ui.components.VeloHeader
import com.velo.vpn.ui.theme.HeartPink
import com.velo.vpn.ui.theme.Muted

@Composable
fun SupportScreen(nav: NavHostController, commerce: CommerceViewModel, accountVm: AccountViewModel) {
    val state by commerce.state.collectAsState()
    val account by accountVm.state.collectAsState()
    val amounts = listOf(50000, 100000, 250000, 500000)
    var selected by remember { mutableIntStateOf(1) }
    var custom by remember { mutableStateOf("") }
    var customMode by remember { mutableStateOf(false) }
    val amount = if (customMode) custom.toIntOrNull() ?: 0 else amounts[selected]
    val hearts = state.config?.supportHeartTiers?.get(amount.toString())

    Scaffold { pad ->
        Column(
            Modifier.fillMaxSize().padding(pad).padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            VeloHeader(showBack = true, hearts = account.hearts, onBack = { nav.popBackStack() })
            Text("حمایت از پروژه", fontSize = 30.sp, fontWeight = FontWeight.ExtraBold)
            Text("با حمایت شما Velo بهتر و پایدارتر می‌شود.", color = Muted)
            Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                Icon(Icons.Default.Favorite, null, tint = HeartPink, modifier = Modifier.size(76.dp))
            }
            Text("انتخاب مبلغ حمایت", fontWeight = FontWeight.Bold)
            amounts.chunked(2).forEach { row ->
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    row.forEach { value ->
                        val i = amounts.indexOf(value)
                        FilterChip(
                            selected = !customMode && selected == i,
                            onClick = { customMode = false; selected = i },
                            label = { Text("%,d تومان".format(value)) },
                            modifier = Modifier.weight(1f),
                        )
                    }
                }
            }
            FilterChip(selected = customMode, onClick = { customMode = true }, label = { Text("مبلغ دلخواه") })
            if (customMode) {
                OutlinedTextField(
                    value = custom,
                    onValueChange = { custom = it.filter(Char::isDigit).take(9) },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("مبلغ به تومان") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    singleLine = true,
                )
            }
            if (hearts != null) Text("هدیه این حمایت: +$hearts قلب", color = HeartPink, fontWeight = FontWeight.Bold)
            PrimaryButton("ادامه و دریافت قلب‌ها") {
                if (amount > 0) nav.navigate(Routes.payment("support", amount = amount))
            }
            Text("پس از تایید پرداخت، قلب‌های مربوطه به حساب شما اضافه می‌شوند.", color = Muted, fontSize = 11.sp)
        }
    }
}
